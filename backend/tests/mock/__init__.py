"""Mock 数据提供 / Mock data provider — 开发模式用，不调 LLM，直接返回预制数据
切换方式：config.yaml 中 set mock_mode: true/false，或环境变量 MOCK_MODE=1/0
"""

from .tick_engine import MockTickEngine
from .world_state import MOCK_WORLD

__all__ = ["MOCK_WORLD", "MockTickEngine"]
