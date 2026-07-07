"""实体覆盖检测 / Entity overlap detection."""

from __future__ import annotations

from typing import Any

ADJACENT_OFFSETS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def _position_of(info: Any) -> tuple[int | None, int | None]:
    if isinstance(info, dict):
        return info.get("position_x", 0), info.get("position_y", 0)
    return getattr(info, "position_x", 0), getattr(info, "position_y", 0)


def build_occupied(
    pcs: dict[str, Any] | None = None,
    actors: dict[str, Any] | None = None,
    scene_objects: list[Any] | None = None,
) -> set[tuple[int, int]]:
    """收集所有实体占用的坐标."""
    occupied: set[tuple[int, int]] = set()
    for src in (pcs, actors):
        if not src:
            continue
        for info in src.values():
            x, y = _position_of(info)
            if x is not None and y is not None:
                occupied.add((x, y))
    if scene_objects:
        for obj in scene_objects:
            x, y = _position_of(obj)
            if x is not None and y is not None:
                occupied.add((x, y))
    return occupied


def dict_without(d: dict[str, Any] | None, key: str) -> dict[str, Any]:
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
