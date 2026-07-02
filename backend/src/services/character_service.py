"""Character Service: State ↔ Engine adapter——角色决策."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.decision import decision_engine
from ..engine.exploration import exploration_engine
from ..engine.observation import observation_engine
from ..engine.talk import talk_engine
from ..graph.state import OverallState
from ..schemas.response import SceneObservation
from ..utils.helpers import get_repo


async def observe_scene(state: OverallState, config: RunnableConfig = None) -> dict:
    """组装角色观察结果 / Build scene observations for characters."""
    scene_id = state.get("scene_id", "")
    pc_ids = await _load_scene_pc_ids(state, config)
    if not pc_ids:
        return {"scene_observations": []}

    all_observations: list[dict] = []
    for pc_id in pc_ids:
        response = await observation_engine.observe_scene(
            world_id=state.get("world_id", ""),
            pc_id=pc_id,
            tick=state.get("tick", 0),
            scene_id=scene_id,
            config=config,
        )
        all_observations.extend(_dump_scene_observation(response))

    return {"scene_observations": all_observations}


async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """基于角色场景观察结果逐个决策 / Decide from per-character scene observations."""
    observations = state.get("scene_observations", [])
    if not observations:
        return {"character_actions": []}

    plot_brief = state.get("plot_brief", "")
    hints = state.get("hints", [])
    scene_id = state.get("scene_id", "")
    actions: list[dict] = []
    for observation in observations:
        action = await decision_engine.decide(
            observation=observation,
            plot_brief=plot_brief,
            hints=hints,
            scene_id=scene_id,
            tick=state.get("tick", 0),
            config=config,
        )
        if action:
            actions.append(action)

    return {"character_actions": actions}


async def act(state: OverallState, config: RunnableConfig = None) -> dict:
    """执行角色动作 / Execute character actions."""
    actions = state.get("character_actions", [])
    if not actions:
        return {}

    tick_message_id = state.get("tick_message_id", "")
    tick = state.get("tick", 0)
    for action in actions:
        await talk_engine.process_talk_action(
            action=action,
            tick_message_id=tick_message_id,
            tick=tick,
            config=config,
        )
        await exploration_engine.process_explore_action(
            action=action,
            tick_message_id=tick_message_id,
            tick=tick,
            config=config,
        )
    return {}


async def _load_scene_pc_ids(state: OverallState, config: RunnableConfig = None) -> list[str]:
    """加载当前 scene 内的 PC 列表 / Load PC ids in current scene."""
    char_repo = get_repo(config, "char")
    scene_id = state.get("scene_id", "")
    pcs = await char_repo.load_pcs() if char_repo else []
    return [pc.id for pc in pcs if getattr(pc, "scene_id", "") == scene_id]


def _dump_scene_observation(response: SceneObservation) -> list[dict]:
    """观察 schema → state dict / Convert observation schema to state dicts."""
    return [response.model_dump()] if response.pc_id else []
