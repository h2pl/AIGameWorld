"""DM Engine: 纯业务逻辑."""

from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...domain.instruction import SceneDirection


_DEMO_PLOTS = [
    ("The party gathers at the Rusty Anchor tavern.", 0),
    ("A hooded stranger slips a cryptic note to Alex.", 1),
    ("Rumors of goblin raids spread through town.", 2),
    ("The town guard calls for able-bodied adventurers.", 3),
    ("A mysterious portal flickers in the old ruins.", 4),
]


def dm_create(req: DMCreateRequest) -> DMCreateResponse:
    """Phase 1: DM 创造情境. Mock. Phase 2 接入 LLM."""
    plot = _DEMO_PLOTS[req.tick % len(_DEMO_PLOTS)]
    direction = SceneDirection(
        featured_pcs=["alex", "maya"],
        featured_actors=["innkeeper", "guard"],
    )
    return DMCreateResponse(
        plot_brief=plot[0],
        scene_direction=direction.model_dump(),
        instructions_out=[direction.model_dump()],
    )


def dm_narrate(req: DMNarrateRequest) -> DMNarrateResponse:
    """Phase 6: DM 叙事. Mock. Phase 2 接入 LLM."""
    action_count = len(req.character_actions)
    action_text = (
        f"Characters take {action_count} action(s)."
        if action_count
        else "The scene is quiet for now..."
    )
    return DMNarrateResponse(
        narrative_out=f"[DM] {req.plot_brief}  {action_text}",
    )
