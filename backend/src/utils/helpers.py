"""共享辅助函数 / Shared helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .collision import load_blocked_tiles
from .logging import get_logger
from .overlap import build_occupied, dict_without, find_vacant  # noqa: F401

if TYPE_CHECKING:
    from langchain_core.runnables.config import RunnableConfig

logger = get_logger(__name__)


def get_llm(config: RunnableConfig | None):
    """从 config 取 LLM 客户端."""
    if config and "configurable" in config:
        llm = config["configurable"].get("llm")
        if llm is None:
            logger.warning("[utils] LLM not available in config")
        return llm
    logger.warning("[utils] No config provided, LLM unavailable")
    return None


def get_repos(config: RunnableConfig | None) -> dict | None:
    """从 config 取完整的 Repo 字典."""
    if config and "configurable" in config:
        repos = config["configurable"].get("repos")
        if repos is None:
            logger.debug("[utils] No repos in config")
        return repos
    logger.debug("[utils] No config provided, repos unavailable")
    return None


def get_repo(config: RunnableConfig | None, name: str):
    """按名取单个 Repo."""
    repos = get_repos(config)
    if repos is None:
        logger.warning("[utils] Repo '%s' not found, repos unavailable", name)
        return None
    repo = repos.get(name)
    if repo is None:
        logger.warning("[utils] Repo '%s' not found in config", name)
    return repo


def is_mock(config: RunnableConfig | None) -> bool:
    """是否 mock 模式."""
    if config and "configurable" in config:
        return config["configurable"].get("mock", False)
    return False


# ═══════════════════════════════════════════════════════════════
# 坐标合法性校验 / Position validation
# ═══════════════════════════════════════════════════════════════


def validate_position(
    x: int,
    y: int,
    pcs: dict[str, Any] | None = None,
    actors: dict[str, Any] | None = None,
    scene: Any | None = None,
    scene_objects: list[Any] | None = None,
) -> tuple[int, int]:
    """校验坐标合法性，不合法时返回最近合法坐标。

    自动检查三类阻塞：
    - 实体占用（PC / Actor 点坐标重叠）
    - 场景物体（SceneObject 坐标占用）
    - 地图碰撞（从 scene.ext_json 解析 collision_rects）
    合法则返回原坐标，不合法则 8 方向搜索最近空位。
    """
    occupied = build_occupied(pcs, actors, scene_objects)
    occupied |= load_blocked_tiles(scene)
    if (x, y) not in occupied:
        return x, y
    for dx, dy in _ADJACENT:
        nx, ny = x + dx, y + dy
        if (nx, ny) not in occupied:
            return nx, ny
    return x, y


_ADJACENT = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
