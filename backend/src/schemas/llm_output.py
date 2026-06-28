"""LLM 结构化输出 Schema——LLM 直接生成的 Pydantic 模型."""

from pydantic import BaseModel, Field


class LLMSceneDirection(BaseModel):
    """LLM 生成的场景导演指令."""
    plot_brief: str = Field(description="1-2 sentence description of the scene for this tick")
    featured_pcs: list[str] = Field(default_factory=list, description="PC IDs to feature")
    featured_actors: list[str] = Field(default_factory=list, description="Actor IDs to feature")


class LLMDMNarrative(BaseModel):
    """LLM 生成的 DM 叙事."""
    narrative: str = Field(description="1-3 paragraph narrative of this tick's events")
