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
    thought: str = Field(
        description="完整的思考过程（2-4句中文）：观察到了什么、联想到哪些记忆、权衡了哪些选择、为什么选这个行动"
    )
    reasoning: str = Field(description="最终决策理由（1-2句中文，总结为什么执行这个动作）")


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


# === Phase 4b: 探索路径 / Explore Path ===
class ExploreOutputSchema(BaseModel):
    """探索输出——LLM 决定去哪探索以及发现什么 / Explore output: destination + explore_record."""

    end_x: int = Field(description="探索目的地 x 坐标，必须在地图范围内，与起点保持 3-10 格距离")
    end_y: int = Field(description="探索目的地 y 坐标，必须在地图范围内，与起点保持 3-10 格距离")
    explore_record: str = Field(
        description="到达目的地后发现或感受到的内容（1-2 句中文，第三人称旁白）"
    )


# === Phase 4c: 场景物体交互 / Scene Object Interaction ===
class InteractOutputSchema(BaseModel):
    """交互输出——LLM 决定交互结果 + 撰写旁白 / Interact output: success + narration."""

    success: bool = Field(description="交互是否成功（基于当前场景、角色能力和物体特性合理判断）")
    narration: str = Field(description="第三人称旁白（1-2 句中文），描述 PC 与物体交互的过程和结果")


# === Phase 4d: 战斗 / Combat ===
class CombatNarrationSchema(BaseModel):
    """战斗旁白输出——LLM 基于战斗日志生成第三人称描述与战斗结果 / Combat narration output."""

    narration: str = Field(description="第三人称战斗旁白（2-3 句中文），基于战斗日志描述交锋过程")
    target_defeated: bool = Field(default=False, description="目标是否在本次交锋中被击败/击杀")
    result: str = Field(
        default="", description="战斗结果一句话总结，例如'目标倒地不起'或'双方仍在僵持'"
    )


# === Phase 2.4: tilemap 语义解读 / Tilemap semantic interpretation ===
class TilemapInterpretationSchema(BaseModel):
    """tilemap 语义摘要 / Semantic summary of a tilemap."""

    summary: str = Field(
        description="一段关于 tilemap 地图的中文语义描述：地形、建筑、出入口、危险区域、氛围等"
    )


# === Phase 2.5: 动态生成场景实体 / Dynamic scene entity generation ===
class GeneratedActorSchema(BaseModel):
    """LLM 动态生成的 Actor 字段 / LLM-generated actor fields."""

    id: str = Field(description="唯一 id，建议使用 actor_前缀 + 英文名小写")
    name: str = Field(description="显示名称")
    role: str = Field(default="", description="身份/职业，如 酒馆老板、巡逻守卫、地精斥候")
    race: str | None = Field(default=None, description="种族，如 human、elf、goblin")
    disposition: str = Field(default="neutral", description="neutral / friendly / hostile")
    status: str = Field(default="active", description="active / dead / inactive")
    personality: str = Field(default="", description="简短性格描述")
    position_x: int = Field(default=0, description="场景内 x 坐标，必须在地图范围内")
    position_y: int = Field(default=0, description="场景内 y 坐标，必须在地图范围内")
    attributes_json: str = Field(
        default='{"strength":10,"dexterity":10,"constitution":10,"intelligence":10,"wisdom":10,"charisma":10}',
        description="JSON 字符串：六维属性",
    )
    combat_json: str = Field(
        default='{"hp":10,"max_hp":10,"ac":10,"attack_bonus":0,"damage_dice":"1d6"}',
        description="JSON 字符串：战斗属性",
    )


class ActorGenerationSchema(BaseModel):
    """批量生成 Actor / Batch actor generation."""

    actors: list[GeneratedActorSchema] = Field(
        default_factory=list, description="为本场景生成的 NPC 列表，通常 2-5 个"
    )


class GeneratedSceneObjectSchema(BaseModel):
    """LLM 动态生成的 SceneObject 字段 / LLM-generated scene object fields."""

    id: str = Field(description="唯一 id，建议使用 obj_前缀 + 英文名小写")
    name: str = Field(description="显示名称")
    object_type: str = Field(
        description="物体类型，必须是 container / door / trap / animal / mechanism / decoration / item_drop 之一"
    )
    interactable: bool = Field(default=True, description="是否可交互")
    position_x: int = Field(default=0, description="场景内 x 坐标，必须在地图范围内")
    position_y: int = Field(default=0, description="场景内 y 坐标，必须在地图范围内")
    interact_data: dict | None = Field(
        default=None, description="交互数据，如容器内容、陷阱 DC、门是否上锁等"
    )


class SceneObjectGenerationSchema(BaseModel):
    """批量生成场景物体 / Batch scene object generation."""

    objects: list[GeneratedSceneObjectSchema] = Field(
        default_factory=list, description="为本场景生成的物体列表，通常 2-5 个"
    )


# === Phase 7: 反思与摘要 / Reflection & Summary ===
class ReflectionOutputSchema(BaseModel):
    """角色反思输出 / Reflection output."""

    arc_analysis: str = Field(default="", description="角色弧线分析（PC）")
    personality_insight: str = Field(default="", description="性格洞察（PC）")
    behavior_summary: str = Field(default="", description="行为模式总结（Actor）")


class SummaryOutputSchema(BaseModel):
    """Tick 摘要输出 / Tick summary output."""

    summary: str = Field(default="", description="事件摘要（1-2 句中文）")
