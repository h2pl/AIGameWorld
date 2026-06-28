"""DM Engine: mock 或 DMAgent 驱动."""

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


async def dm_create(
    req: DMCreateRequest,
    agent=None,  # Optional[DMAgent] for Phase 2+
) -> DMCreateResponse:
    """Phase 1: DM 创造情境。agent 提供时走 DMAgent，否则走 mock."""
    if agent is not None:
        result = await agent.create_situation(plot_brief_prev=req.plot_brief)
        direction = SceneDirection(
            featured_pcs=result["scene_direction"].get("featured_pcs", []),
            featured_actors=result["scene_direction"].get("featured_actors", []),
        )
        return DMCreateResponse(
            instructions_out=result["instructions_out"],
            plot_brief=result["plot_brief"],
            scene_direction=direction.model_dump(),
        )

    return _mock_create(req)


async def dm_narrate(
    req: DMNarrateRequest,
    agent=None,  # Optional[DMAgent] for Phase 2+
) -> DMNarrateResponse:
    """Phase 6: DM 叙事。agent 提供时走 DMAgent，否则走 mock."""
    if agent is not None:
        result = await agent.narrate(
            plot_brief=req.plot_brief,
            character_actions=req.character_actions,
        )
        return DMNarrateResponse(narrative_out=result["narrative"])

    return _mock_narrate(req)


def _mock_create(req: DMCreateRequest) -> DMCreateResponse:
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


def _mock_narrate(req: DMNarrateRequest) -> DMNarrateResponse:
    action_count = len(req.character_actions)
    action_text = (
        f"Characters take {action_count} action(s)."
        if action_count
        else "The scene is quiet for now..."
    )
    return DMNarrateResponse(
        narrative_out=f"{req.plot_brief}  {action_text}",
    )
