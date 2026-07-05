"""共享辅助函数 / Shared helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .logging import get_logger

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
# 角色站位防重叠 / Character overlap avoidance
# ═══════════════════════════════════════════════════════════════


def build_occupied_set(
    pc_state_map: dict[str, dict] | None,
    actor_state_map: dict[str, dict] | None = None,
    exclude_id: str = "",
) -> set[tuple[int, int]]:
    """收集所有角色占用的坐标（排除 exclude_id）/ Collect all occupied positions, excluding one id."""
    occupied: set[tuple[int, int]] = set()
    for src in (pc_state_map, actor_state_map):
        if not src:
            continue
        for cid, info in src.items():
            if cid == exclude_id:
                continue
            x = info.get("position_x", 0)
            y = info.get("position_y", 0)
            if x or y:
                occupied.add((x, y))
    return occupied


_ADJACENT_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def find_vacant_adjacent(
    tx: int,
    ty: int,
    occupied: set[tuple[int, int]],
    map_width: int = 100,
    map_height: int = 100,
) -> tuple[int, int]:
    """在目标周围找一个未被占用的相邻格 / Find a vacant adjacent cell near target."""
    for dx, dy in _ADJACENT_OFFSETS:
        nx, ny = tx + dx, ty + dy
        if 0 <= nx < map_width and 0 <= ny < map_height and (nx, ny) not in occupied:
            return nx, ny
    return tx, ty  # 全被占则原地不动 / All occupied, stay put
