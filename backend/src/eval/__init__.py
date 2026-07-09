"""RPG 世界状态评估包 / RPG World State Evaluation Package.

五维度评估体系：
- world_state:     世界状态正确性（坐标、不变量、HP 一致性）
- npc_consistency: NPC 行为与设定一致性（对话、位置、状态）
- game_rules:      游戏规则合规（DnD 规则、移动限制、战斗逻辑）
- causality_memory: 事件因果性 + 记忆连贯性
"""

from .base import DimensionReport, EvalIssue, Severity, WorldEvalReport
from .event_causality import evaluate_event_causality
from .npc_consistency import evaluate_npc_consistency
from .rules import evaluate_game_rules
from .world_state import evaluate_world_state

__all__ = [
    "DimensionReport",
    "EvalIssue",
    "Severity",
    "WorldEvalReport",
    "evaluate_world_state",
    "evaluate_npc_consistency",
    "evaluate_game_rules",
    "evaluate_event_causality",
]
