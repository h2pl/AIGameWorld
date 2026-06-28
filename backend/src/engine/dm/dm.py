"""DM Engine: 纯业务逻辑——mock 或 LLM."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ...schemas.request import DMCreateRequest, DMNarrateRequest
from ...schemas.response import DMCreateResponse, DMNarrateResponse
from ...schemas.llm_output import LLMSceneDirection, LLMDMNarrative
from ...domain.instruction import SceneDirection

_DEMO_PLOTS = [
    ("The party gathers at the Rusty Anchor tavern.", 0),
    ("A hooded stranger slips a cryptic note to Alex.", 1),
    ("Rumors of goblin raids spread through town.", 2),
    ("The town guard calls for able-bodied adventurers.", 3),
    ("A mysterious portal flickers in the old ruins.", 4),
]

_PROMPTS = Environment(loader=FileSystemLoader(Path(__file__).parent.parent.parent / "prompts"))


def dm_create(
    req: DMCreateRequest,
    llm=None,  # Optional[LLMClient] for Phase 2
    pcs: list[str] | None = None,
    actors: list[str] | None = None,
) -> DMCreateResponse:
    """Phase 1: DM 创造情境. Phase 2 接入 LLM.

    When llm is provided: build prompt from template → call LLM → parse structured output.
    When llm is None: use demo data.
    """
    if llm is None:
        return _mock_create(req)

    pcs = pcs or []
    actors = actors or []
    prompt = _PROMPTS.get_template("dm_create.jinja").render(
        tick=req.tick,
        plot_brief=req.plot_brief,
        pcs=pcs,
        actors=actors,
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        result = llm.structured(messages, LLMSceneDirection)
        direction = SceneDirection(
            featured_pcs=result.featured_pcs,
            featured_actors=result.featured_actors,
        )
        return DMCreateResponse(
            plot_brief=result.plot_brief,
            scene_direction=direction.model_dump(),
            instructions_out=[direction.model_dump()],
        )
    except Exception:
        # 降级到 mock / Fallback to mock
        return _mock_create(req)


def dm_narrate(
    req: DMNarrateRequest,
    llm=None,  # Optional[LLMClient] for Phase 2
) -> DMNarrateResponse:
    """Phase 6: DM 叙事. Phase 2 接入 LLM."""
    if llm is None:
        return _mock_narrate(req)

    prompt = _PROMPTS.get_template("dm_narrate.jinja").render(
        plot_brief=req.plot_brief,
        scene_direction=req.scene_direction,
        character_actions=req.character_actions,
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        result = llm.structured(messages, LLMDMNarrative)
        return DMNarrateResponse(narrative_out=result.narrative)
    except Exception:
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
