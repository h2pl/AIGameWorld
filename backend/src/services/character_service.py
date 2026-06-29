"""Character Service: State ↔ Engine adapter.

Service 只管 State↔Request↔Response，所有外部资源 Engine 自己从 config 取。
"""
import logging

from langchain_core.runnables.config import RunnableConfig

from ..engine.character import actor_decide as actor_engine
from ..engine.character import pc_decide as pc_engine
from ..graph.state import CharacterAgentState, CharacterSubState
from ..schemas.request import ActorDecideRequest, PCDecideRequest

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Send fan-out: 单角色决策 agent 节点 / per-character agent node
# ═══════════════════════════════════════════════════════════════

async def character_agent(state: CharacterAgentState, config: RunnableConfig = None) -> dict:
    """P3-3: 单角色决策——由 Send() fan-out 并行调用 / Single-character decision."""
    character_id = state.get("character_id", "")
    character_type = state.get("character_type", "pc")
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)

    try:
        if character_type == "pc":
            action = await pc_engine.pc_decide(
                PCDecideRequest(pc_id=character_id, plot_brief=plot_brief, tick=tick),
                config=config,
            )
        else:
            action = await actor_engine.actor_decide(
                ActorDecideRequest(actor_id=character_id, plot_brief=plot_brief, tick=tick),
                config=config,
            )
        if action:
            return {"character_actions": [action.model_dump()]}
    except Exception:
        logger.exception("character_agent failed for %s %s, fallback wait", character_type, character_id)
        return {"character_actions": [{
            "character_id": character_id,
            "action_type": "wait",
            "target": None,
            "reasoning": "暂时不动，观察局势。",
        }]}
    return {"character_actions": []}


# ═══════════════════════════════════════════════════════════════
# 保留: 原串行接口，供测试使用 / legacy serial interface for tests
# ═══════════════════════════════════════════════════════════════

async def pc_decide(state: CharacterSubState, config: RunnableConfig = None) -> dict:
    """Phase 3: 遍历 featured PCs 串行决策（测试用 / for tests）."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for pc_id in direction.get("featured_pcs", []):
        action = await pc_engine.pc_decide(
            PCDecideRequest(pc_id=pc_id, plot_brief=plot_brief, tick=tick),
            config=config,
        )
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}


async def actor_decide(state: CharacterSubState, config: RunnableConfig = None) -> dict:
    """Phase 3: 遍历 featured Actors 串行决策（测试用 / for tests）."""
    direction = state.get("scene_direction", {})
    plot_brief = state.get("plot_brief", "")
    tick = state.get("tick", 0)
    actions = []
    for actor_id in direction.get("featured_actors", []):
        action = await actor_engine.actor_decide(
            ActorDecideRequest(actor_id=actor_id, plot_brief=plot_brief, tick=tick),
            config=config,
        )
        if action:
            actions.append(action.model_dump())
    return {"character_actions": actions}
