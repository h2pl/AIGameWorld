"""地图碰撞检测 / Map collision detection.

基于 scene.ext_json.collision_rects 展开为阻塞瓦片集合。
"""

import json

from ..domain.scene import Scene


def load_blocked_tiles(scene: Scene | dict | None) -> set[tuple[int, int]]:
    """从场景 ext_json 解析 collision_rects 并展开为阻塞瓦片坐标集合."""
    if scene is None:
        return set()
    try:
        raw = scene.get("ext_json", "{}") if isinstance(scene, dict) else scene.ext_json
        ext = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError, AttributeError):
        return set()

    rects: list[dict] = ext.get("collision_rects", [])
    blocked: set[tuple[int, int]] = set()
    for r in rects:
        for dx in range(r.get("w", 0)):
            for dy in range(r.get("h", 0)):
                blocked.add((r["x"] + dx, r["y"] + dy))
    return blocked
