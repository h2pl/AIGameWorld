"""DM Agent——情境创造者。per design/04-agent-layer.md §5."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import SystemMessage, HumanMessage

from .llm_client import LLMClient
from ..schemas.llm_output import DMOutput, DMNarrativeSchema, SceneDirectionOutput

logger = logging.getLogger(__name__)

_PROMPTS = Environment(loader=FileSystemLoader(Path(__file__).parent / "prompts"))

_DM_SYSTEM_PROMPT = """你是 AIGameWorld 的 DM（Dungeon Master），负责一个 DND 风格虚拟世界的情境创造与叙事。

你的职责：
1. 创造情境（Phase 1）：搭舞台、设挑战、指定参演人员、注入配角动机
2. 叙事渲染（Phase 6）：基于实际执行结果讲故事

铁律：
- 你不扮演任何角色，不替任何角色做决策
- 你不写角色的对话内容
- 你不决定数值，数值由规则引擎计算
- 你创造情境，角色自己决定如何应对"""


class DMAgent:
    """DM Agent——情境创造 + 叙事渲染。per §5.3."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def create_situation(
        self,
        world_snapshot: dict | None = None,
        story_arcs: list | None = None,
        story_hooks: list | None = None,
        dm_memory: dict | None = None,
        plot_brief_prev: str = "",
        pacing: dict | None = None,
    ) -> dict:
        """Phase 1: 创造情境。per §5.3."""
        context = {
            "story_arcs": story_arcs or [],
            "active_hooks": [h for h in (story_hooks or []) if h.get("status") == "planted"],
            "recent_summary": (dm_memory or {}).get("recent_summary", ""),
            "plot_brief_prev": plot_brief_prev,
            "pacing": pacing or {},
        }

        prompt = _PROMPTS.get_template("dm_create.jinja").render(**context)
        result = await self.llm.call_structured(
            "dm_create",
            DMOutput,
            [SystemMessage(content=_DM_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            fallback=lambda: _create_fallback(),
        )

        if result is None:
            return _fallback_situation()

        return {
            "instructions_out": result.instructions,
            "plot_brief": result.plot_brief,
            "scene_direction": result.scene_direction.model_dump(),
        }

    async def narrate(
        self,
        plot_brief: str,
        character_actions: list,
        events: list | None = None,
        combat_result: dict | None = None,
        cast_changes: list | None = None,
    ) -> dict:
        """Phase 6: 叙事渲染。per §5.3."""
        prompt = _PROMPTS.get_template("dm_narrate.jinja").render(
            plot_brief=plot_brief,
            character_actions=character_actions,
            events=events or [],
            combat_result=combat_result,
            cast_changes=cast_changes or [],
        )
        result = await self.llm.call_structured(
            "dm_narrate",
            DMNarrativeSchema,
            [SystemMessage(content=_DM_SYSTEM_PROMPT), HumanMessage(content=prompt)],
            fallback=lambda: DMNarrativeSchema(narrative="（DM 沉默了...）"),
        )

        return {
            "narrative": result.narrative,
            "branch_points": [bp.model_dump() for bp in result.branch_points],
            "hooks_resolved": result.hooks_resolved,
        }


def _create_fallback() -> DMOutput:
    """降级输出——最小情境。per §2.3."""
    return DMOutput(
        instructions=[],
        plot_brief="平静的一天，没有特别事件。",
        scene_direction=SceneDirectionOutput(mood="neutral"),
    )


def _fallback_situation() -> dict:
    return {
        "instructions_out": [],
        "plot_brief": "平静的一天，没有特别事件。",
        "scene_direction": {"mood": "neutral"},
    }
