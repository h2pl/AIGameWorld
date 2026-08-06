"""Party Service: 团体（主角团）相关逻辑 / Party-level (team) logic.

负责主角团作为一个整体的协同行为，每个 tick 都会执行：
  - party_discuss        —— 始终走 LLM 的集体讨论，只产出多人对话（信息交流），不决定场景去留
  - party_decide_scene   —— 由 LLM 裁决本 tick 是否切换主场景（与讨论是两个独立节点）

与 world_init / tick_init 的边界：
  - world_init  ：整个世界只执行一次的初始化，由 orchestrator.run_tick 在每 tick 入口前
                  调用 ensure_world_initialized 幂等完成，完全在 tick 主图之外。
  - tick_init   ：每个 tick 都执行的纯初始化（出生点分配、事件截屏等）
  - party       ：每个 tick 都执行的团体协同（讨论 + 决策）
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ..domain.event import TickEvent, TickEventType
from ..domain.scene import Scene
from ..engine.identity import map_identity
from ..graph.state import OverallState
from ..schemas.llm_output import PartyDecisionSchema, PartyDiscussionSchema
from ..utils.helpers import assign_spawn_positions, get_llm, get_repo, is_mock
from ..utils.logging import get_logger, trace_node

logger = get_logger(__name__)


async def _list_available_scenes(config, world_id: str) -> list[Scene]:
    """列出当前世界可用场景 / list available scenes."""
    scene_repo = get_repo(config, "scene")
    if not scene_repo:
        return []
    return await scene_repo.list_scenes(world_id)


def _emit_party_discuss_event(
    state: OverallState,
    current: str,
    dialogue: list,
) -> list:
    """把集体讨论对话打包进 PARTY_DISCUSS 事件 / emit party_discuss event.

    讨论只负责信息交流，不决定场景去留：target 强制回填 current、switched=False。
    """
    event = TickEvent(
        type=TickEventType.PARTY_DISCUSS,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": current,
            "dialogue": dialogue,
            "target_scene_id": current,
            "reason": "",
            "switched": False,
        },
    )
    return [*list(state.get("tick_events", [])), event]


def _emit_party_decide_event(
    state: OverallState,
    current: str,
    target: str,
    reason: str,
) -> list:
    """把集体决策（是否切换主场景）打包进 PARTY_DECIDE 事件 / emit party_decide event."""
    event = TickEvent(
        type=TickEventType.PARTY_DECIDE,
        tick=state.get("tick", 0),
        world_id=state.get("world_id", ""),
        payload={
            "scene_id": current,
            "target_scene_id": target,
            "reason": reason,
            "switched": target != current,
        },
    )
    return [*list(state.get("tick_events", [])), event]


def _apply_scene(
    target: str, pcs: dict, available: list[Scene], actors: dict | None = None
) -> dict:
    """把目标场景应用到 PC：统一 scene_id 并把所有 PC 分配到该场景出生点附近。

    坐标分配与 scene_id 同步在此处完成，而不是依赖下游用 scene_id 反推是否切换——
    否则 party 已把 scene_id 提前刷成当前场景，下游判断会恒为 False、老家坐标从不重置。
    出生点本身就在地图范围内，因此分配后坐标必然合法、不会越界。
    """
    if not target:
        return {"current_scene_id": ""}
    scene = next((s for s in available if s.id == target), None)
    for pc in pcs.values():
        pc.scene_id = target
    if scene is not None:
        assign_spawn_positions(list(pcs.values()), scene, actors)
    return {"current_scene_id": target, "pcs": pcs}


@trace_node("party.discuss")
async def party_discuss(state: OverallState, config: RunnableConfig = None) -> dict:
    """集体讨论：始终走 LLM，只产出多人对话（信息交流），不决定场景去留.

    - 所有 tick 都执行，current_scene_id 由上游保证非空（world_init 在首个 tick 前写入
      world.current_scene_id；后续每 tick 的裁决结果在 persist_tick 末尾统一落库）。
    - LLM 生成每个 PC 轮流发言的对话（纯交流）；讨论结果不影响场景切换，
      场景决策交由 party_decide_scene 节点独立裁决。
    - 讨论节点只写 PARTY_DISCUSS 事件（target=current, switched=False），不更新 current_scene_id。
    """
    world_id = state.get("world_id", "")
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})

    available = await _list_available_scenes(config, world_id)
    # current_scene_id 由 world_init / party.decide_scene 确定性保证非空；
    # 讨论节点不决定场景，target 恒等于 current，无需 fallback
    current = state.get("current_scene_id", "")
    target = current

    llm = get_llm(config)
    dialogue: list = []
    if llm is not None and not is_mock(config):
        # 真实模式：始终走 LLM 生成多人对话（信息交流），不降级
        dialogue = await _llm_discuss(
            llm, state.get("tick", 1), world_id, pcs, current, available, config=config
        )
    elif is_mock(config):
        # mock 模式：从 mock 数据集读取预置对话，保证演示有内容
        from ..llm.mock_data import get_mock

        mock = get_mock("party_discuss", state.get("mock_dataset", ""))
        dialogue = mock.get("dialogue", [])

    applied = _apply_scene(target, pcs, available, actors)
    applied["tick_events"] = _emit_party_discuss_event(state, current=current, dialogue=dialogue)
    return applied


@trace_node("party.decide_scene")
async def party_decide_scene(state: OverallState, config: RunnableConfig = None) -> dict:
    """集体决策：由 LLM 裁决本 tick 是否切换主场景（与讨论是两个独立节点）.

    - 读取 current_scene_id + 可用场景列表，LLM 输出目标场景 id + 理由。
    - 决策结果写入 PARTY_DECIDE 事件，并写入 state 的 current_scene_id（所有 PC 的 scene_id 统一同步）；
      落库由 persist_tick 在 tick 末尾统一完成。
    - 无可切换场景（场景数<=1）或 LLM 不可用（非 mock 缺失配置）时，沿用当前场景，
      不产出切场景事件（保持 switched=False）。
    """
    world_id = state.get("world_id", "")
    pcs = state.get("pcs", {})
    actors = state.get("actors", {})

    available = await _list_available_scenes(config, world_id)
    valid_ids = {s.id for s in available}
    # current_scene_id 由 world_init 保证在首个 tick 前已写入且非空，无需 fallback
    current = state.get("current_scene_id", "")

    target = current
    reason = ""

    # 无可选场景 → 停留当前 / no alternative → stay
    if len(valid_ids) <= 1:
        reason = "无可切换场景，停留当前"
    elif is_mock(config):
        # mock 模式：沿用当前场景（不切场，保证演示稳定）
        reason = "沿用当前场景"
    else:
        llm = get_llm(config)
        if llm is None:
            reason = "沿用当前场景"
        else:
            result = await _llm_decide_scene(
                llm, state.get("tick", 0), world_id, pcs, current, available, config=config
            )
            target = result.get("target_scene_id") or current
            reason = result.get("reason", "")
            if target not in valid_ids:
                logger.warning(
                    "[party] party_decide_scene returned invalid scene=%s, keep %s",
                    target,
                    current,
                )
                target = current

    # 仅把裁决结果写入 state（current_scene_id + 各 PC.scene_id），
    # 落库统一由 data_service.persist_tick 在 tick 末尾完成
    applied = _apply_scene(target, pcs, available, actors)
    applied["tick_events"] = _emit_party_decide_event(
        state, current=current, target=target, reason=reason
    )
    return applied


def _build_pc_lines(pcs: dict) -> list[str]:
    """构建团队成员的背景行（含长期目标/价值观/性格）/ Build party member background lines."""
    lines = []
    for pc in pcs.values():
        ident = map_identity(pc)
        parts = [f"- {ident['name']}（id={ident['id']}）"]
        if ident["role"]:
            parts.append(f"身份={ident['role']}")
        if ident["long_term_goal"]:
            parts.append(f"长期目标={ident['long_term_goal']}")
        if ident["core_values"]:
            parts.append(f"价值观={ident['core_values']}")
        if ident["personality"]:
            parts.append(f"性格={ident['personality']}")
        lines.append("，".join(parts))
    return lines


async def _llm_discuss(llm, tick, world_id, pcs, current, available, config=None) -> list:
    """LLM 集体讨论：只生成多人对话 / LLM party discussion — dialogue only."""
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    _ROOT = Path(__file__).parent.parent / "prompts"
    _ENV = Environment(loader=FileSystemLoader(_ROOT))

    pc_lines = _build_pc_lines(pcs)
    scene_lines = [f"- {s.id}：{s.name}（{s.type}）" for s in available]

    system = _ENV.get_template("party/_party_system.jinja").render()
    prompt = _ENV.get_template("party/party_discussion.jinja").render(
        tick=tick,
        current=current,
        pcs="\n".join(pc_lines),
        scenes="\n".join(scene_lines),
    )
    try:
        result = await llm.call_structured(
            "party_discuss",
            PartyDiscussionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
        )
        return [t.model_dump() for t in result.dialogue]
    except Exception as e:
        logger.warning("[party] party_discuss LLM failed: %s", e)
        return []


async def _llm_decide_scene(llm, tick, world_id, pcs, current, available, config=None) -> dict:
    """LLM 集体决策：裁决是否切换主场景 / LLM party decision on scene switch."""
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    _ROOT = Path(__file__).parent.parent / "prompts"
    _ENV = Environment(loader=FileSystemLoader(_ROOT))

    pc_lines = _build_pc_lines(pcs)
    scene_lines = [f"- {s.id}：{s.name}（{s.type}）" for s in available]

    system = _ENV.get_template("party/_party_system.jinja").render()
    prompt = _ENV.get_template("party/party_decide.jinja").render(
        tick=tick,
        current=current,
        pcs="\n".join(pc_lines),
        scenes="\n".join(scene_lines),
    )
    try:
        result = await llm.call_structured(
            "party_decide",
            PartyDecisionSchema,
            [SystemMessage(content=system), HumanMessage(content=prompt)],
        )
        return {
            "target_scene_id": result.target_scene_id or current,
            "reason": result.reason,
        }
    except Exception as e:
        logger.warning("[party] party_decide LLM failed: %s, keep %s", e, current)
        return {"target_scene_id": current, "reason": ""}
