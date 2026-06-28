"""WorldState Repository 接口 / Repository interface.

定义领域层需要的数据操作，不绑定具体存储技术。
"""
from abc import ABC, abstractmethod
from typing import Any


class WorldStateRepo(ABC):
    """Tick State 仓储接口 / Repository for tick-level state."""

    @abstractmethod
    async def init(self) -> None:
        """初始化 / Initialize storage."""
        ...

    @abstractmethod
    async def save(self, state: dict[str, Any], tick: int) -> None:
        """保存当前 tick 状态 / Save tick state."""
        ...

    @abstractmethod
    async def load(self, tick: int) -> dict[str, Any] | None:
        """读取指定 tick 状态 / Load tick state."""
        ...

    @abstractmethod
    async def load_latest(self) -> dict[str, Any] | None:
        """读取最新状态 / Load latest state."""
        ...

    @abstractmethod
    async def rollback(self, tick: int) -> None:
        """回退到指定 tick / Rollback to tick."""
        ...

    @abstractmethod
    async def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取历史 / Get tick history."""
        ...
