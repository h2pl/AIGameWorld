"""Character Service: State ↔ Engine adapter——角色决策."""

from langchain_core.runnables.config import RunnableConfig

from ..engine.decision import decision_engine
from ..engine.exploration import exploration_engine
from ..engine.perception import perception_engine
from ..engine.talk import talk_engine
from ..graph.state import OverallState


async def perceive(state: OverallState, config: RunnableConfig = None) -> dict:
    """组装角色感知上下文 / Build perceived context for characters."""
    perceived_context = await perception_engine.perceive_characters(
        world_id=state.get("world_id", ""),
        tick=state.get("tick", 0),
        scene_id=state.get("scene_id", ""),
        plot_brief=state.get("plot_brief", ""),
        hints=state.get("hints", []),
        config=config,
    )
    return {"perceived_character_contexts": perceived_context}


async def decide(state: OverallState, config: RunnableConfig = None) -> dict:
    """基于角色感知上下文逐个决策 / Decide from perceived character contexts."""
    contexts = state.get("perceived_character_contexts", [])
    if not contexts:
        return {"character_actions": []}

    actions = await decision_engine.process_characters(
        contexts=contexts,
        tick=state.get("tick", 0),
        config=config,
    )
    return {"character_actions": actions}


async def act(state: OverallState, config: RunnableConfig = None) -> dict:
    """执行角色动作 / Execute character actions."""
    actions = state.get("character_actions", [])
    tick_message_id = state.get("tick_message_id", "")
    tick = state.get("tick", 0)
    await talk_engine.process_talk_actions(
        actions=actions,
        tick_message_id=tick_message_id,
        tick=tick,
        config=config,
    )
    await exploration_engine.process_explore_actions(
        actions=actions,
        tick_message_id=tick_message_id,
        tick=tick,
        config=config,
    )
    return {}
