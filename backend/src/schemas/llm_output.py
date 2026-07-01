"""LLM 结构化输出 Schema。per design/04-agent-layer.md §5.4 + design/06-llm-dev-guide.md §2.1."""

from pydantic import BaseModel, Field


class DMOutput(BaseModel):
    """DM 创造情境输出。per §5.4."""

    hints: list[str] = Field(default_factory=list, description="环境提示信息")
    plot_brief: str = Field(description="本步剧情梗概（2-3句）")
    scene_id: str = ""


class DMNarrativeSchema(BaseModel):
    """DM 叙事输出。per §5.4."""

    narrative: str = Field(description="故事文本（3-5句，第三人称 DND DM 口吻）")


# === Phase 3: 角色决策 / Character Decision ===
_VALID_ACTIONS = {"move", "talk", "attack", "interact", "wait"}


class CharacterActionSchema(BaseModel):
    """PC/Actor 行动决策输出。per design/04-agent-layer.md §6."""

    action_type: str = Field(description="move / talk / attack / interact / wait")
    target: str | None = Field(default=None, description="目标角色id或场景对象id")
    reasoning: str = Field(description="决策理由（2-3句中文，体现角色弧/价值观）")
