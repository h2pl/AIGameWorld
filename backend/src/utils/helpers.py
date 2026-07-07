"""共享辅助函数 / Shared helper functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .collision import load_blocked_tiles
from .logging import get_logger
from .overlap import build_occupied, dict_without, find_vacant  # noqa: F401

if TYPE_CHECKING:
    from ..domain import Actor, PlayerCharacter, Scene, SceneObject
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


def assign_spawn_positions(
    pcs: list[PlayerCharacter],
    scene: Scene,
    actors: dict[str, Actor] | None = None,
    spawn_radius: int = 2,
) -> list[PlayerCharacter]:
    """为未设置坐标的 PC 分配出生点坐标，直接修改领域模型并返回。

    以 scene 的 spawn 为中心螺旋搜索，避开 actors 占位和地图碰撞。
    """
    if not pcs or scene is None:
        return pcs

    spawn_x = scene.spawn_x
    spawn_y = scene.spawn_y

    occupied = build_occupied(None, actors)
    occupied |= load_blocked_tiles(scene)

    offsets = [
        (dx, dy)
        for r in range(spawn_radius + 1)
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if max(abs(dx), abs(dy)) == r
    ]

    for pc in pcs:
        x, y = spawn_x, spawn_y
        for dx, dy in offsets:
            cx, cy = spawn_x + dx, spawn_y + dy
            if (cx, cy) not in occupied:
                x, y = cx, cy
                break
        else:
            x, y = find_vacant(spawn_x, spawn_y, occupied)

        pc.position_x = x
        pc.position_y = y
        occupied.add((x, y))

    return pcs


def validate_position(
    x: int,
    y: int,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    scene: Scene | None = None,
    scene_objects: list[SceneObject] | None = None,
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
