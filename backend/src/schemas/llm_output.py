"""LLM 结构化输出 Schema。per design/04-agent-layer.md §5.4 + design/06-llm-dev-guide.md §2.1."""

from pydantic import BaseModel, Field


class SceneDirectionOutput(BaseModel):
    """DM 导演指令——指定本步参演人员."""

    featured_pcs: list[str] = Field(default_factory=list)
    featured_actors: list[str] = Field(default_factory=list)
    actor_motivations: dict[str, str] = Field(default_factory=dict)
    mood: str = "neutral"


class BranchPoint(BaseModel):
    """叙事分支点."""

    decision_maker: str = ""
    decision: str = ""
    consequence: str = ""


class DMOutput(BaseModel):
    """DM 创造情境输出。per §5.4."""

    instructions: list[str] = Field(default_factory=list, description="玩家可执行的行动建议")
    plot_brief: str = Field(description="本步剧情梗概（2-3句）")
    scene_direction: SceneDirectionOutput = Field(default_factory=SceneDirectionOutput)


class DMNarrativeSchema(BaseModel):
    """DM 叙事输出。per §5.4."""

    narrative: str = Field(description="故事文本（3-5句，第三人称 DND DM 口吻）")
    branch_points: list[BranchPoint] = Field(default_factory=list)
    hooks_resolved: list[str] = Field(default_factory=list)
