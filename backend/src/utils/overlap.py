"""实体覆盖检测 / Entity overlap detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain import Actor, PlayerCharacter, SceneObject

ADJACENT_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def build_occupied(
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    scene_objects: list[SceneObject] | None = None,
) -> set[tuple[int, int]]:
    """收集所有实体占用的坐标."""
    occupied: set[tuple[int, int]] = set()
    for src in (pcs, actors):
        if not src:
            continue
        for info in src.values():
            occupied.add((info.position_x, info.position_y))
    if scene_objects:
        for obj in scene_objects:
            occupied.add((obj.position_x, obj.position_y))
    return occupied


def dict_without(d: dict | None, key: str) -> dict:
    """返回去除指定 key 的副本."""
    if not d:
        return {}
    return {k: v for k, v in d.items() if k != key}


def find_vacant(tx: int, ty: int, occupied: set[tuple[int, int]]) -> tuple[int, int]:
    """在目标周围找未被占用的相邻格."""
    for dx, dy in ADJACENT_OFFSETS:
        nx, ny = tx + dx, ty + dy
        if (nx, ny) not in occupied:
            return nx, ny
    return tx, ty
