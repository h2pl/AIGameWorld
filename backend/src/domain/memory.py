"""记忆领域模型 / Memory Domain Model."""

from pydantic import BaseModel


class Memory(BaseModel):
    """一条角色记忆 / A single character memory."""

    id: str
    character_id: str
    content: str  # 记忆文本 / memory text
    tick: int = 0
    importance: int = 1  # 重要性 1-10
    memory_type: str = "observation"  # observation / reflection


# 重要性评分表 / Importance scoring table (per 04-agent-layer.md §8.4)
IMPORTANCE_MAP: dict[str, int] = {
    "combat_hit": 8,  # 战斗命中
    "combat_miss": 7,  # 战斗被命中
    "character_death": 10,  # 角色死亡
    "dialogue": 4,  # 对话
    "move": 1,  # 移动
    "trade": 5,  # 交易
    "quest_trigger": 8,  # 任务触发
    "scene_interact": 4,  # 场景交互
    "cast_change": 9,  # 主角团变动
    "default": 2,
}


def importance_of(event_type: str) -> int:
    """根据事件类型返回重要性分数."""
    return IMPORTANCE_MAP.get(event_type, IMPORTANCE_MAP["default"])
