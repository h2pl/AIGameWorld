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
# combat 预留：战斗结算尚未接入 act 执行层 / combat reserved: not yet wired into the act phase
# TODO: 实现 combat 动作在 act 阶段的执行（调用 combat_engine）
_VALID_ACTIONS = {"talk", "interact", "combat", "explore", "wait"}
_VALID_TARGET_TYPES = {"pc", "actor", "scene_object"}


class CharacterActionSchema(BaseModel):
    """PC/Actor 行动决策输出。per design/04-agent-layer.md §6."""

    action_type: str = Field(description="talk / interact / combat / explore / wait")
    target_id: str | None = Field(default=None, description="目标 id（pc/actor/场景物体）")
    target_type: str | None = Field(default=None, description="pc / actor / scene_object")
    reasoning: str = Field(description="决策理由（2-3句中文，结合当前场景和附近的人）")


class PCDecideListSchema(BaseModel):
    """PC 多行动决策列表——每 tick 可执行 1~3 个动作 / PC multi-action decision list."""

    actions: list[CharacterActionSchema] = Field(
        default_factory=list,
        description="按顺序执行的行动列表，通常 1~3 个",
    )


# === Phase 4: 双人对话 / Two-character Dialogue ===
class DialogueTurnSchema(BaseModel):
    """单轮对话 / A single dialogue turn."""

    speaker_id: str = Field(description="说话者 id，必须精确匹配给定的 id，不要用名字")
    text: str = Field(description="该轮台词（简体中文）")


class DialogueSchema(BaseModel):
    """双人对话——单次 LLM 调用生成多轮 / Two-character dialogue generated in one call."""

    turns: list[DialogueTurnSchema] = Field(
        default_factory=list, description="按顺序排列的对话轮次，从发起者开始"
    )
