"""Scene Observation Engine——观察当前场景并返回观察结果."""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...schemas.response import SceneObservation
from ...utils.helpers import get_repo

# 模块日志 / Module logger
logger = logging.getLogger("aw.eng.char")


async def observe_scene(
    world_id: str,
    pc_id: str,
    tick: int,
    scene_id: str,
    config: RunnableConfig = None,
) -> SceneObservation:
    """观察单个角色所在场景 / Observe the current scene for a single character."""
    # 角色与场景仓储 / Character and scene repositories
    char_repo = get_repo(config, "char")
    scene_repo = get_repo(config, "scene")
    if not char_repo:
        logger.warning("[character] no char_repo, skip observe_scene")
        return SceneObservation()

    pcs = await char_repo.load_pcs(world_id) if world_id else []
    actors = await char_repo.load_actors(world_id) if world_id else []
    all_chars = [("pc", pc) for pc in pcs] + [("actor", actor) for actor in actors]

    # 当前场景内的角色池 / Character pool limited to the current scene
    # actor 当前是绑定 scene 的，pc 未来可能跨 scene，因此这里统一按 scene_id 过滤。
    scene_chars = [
        (char_type, char)
        for char_type, char in all_chars
        if getattr(char, "scene_id", "") == scene_id
    ]

    scene_object_ids = await scene_repo.get_object_ids(scene_id) if scene_repo and scene_id else []

    # 为当前 scene 内的目标 PC 生成观察结果 / Build observation for the target PC in current scene
    for _char_type, char in scene_chars:
        if char.id != pc_id:
            continue

        # 角色只观察当前 scene 的附近角色 / Characters only observe nearby people in the current scene
        nearby_characters = [
            (other_type, other.id)
            for other_type, other in scene_chars
            if other.id != char.id
            and _distance(
                getattr(char, "position_x", 0),
                getattr(char, "position_y", 0),
                getattr(other, "position_x", 0),
                getattr(other, "position_y", 0),
            )
            <= 5
        ]

        return SceneObservation(
            pc_id=char.id,
            nearby_pc_ids=[
                other_id for other_type, other_id in nearby_characters if other_type == "pc"
            ],
            nearby_actor_ids=[
                other_id for other_type, other_id in nearby_characters if other_type == "actor"
            ],
            scene_object_ids=scene_object_ids,
        )

    return SceneObservation()


def _distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x1 - x2) + abs(y1 - y2)
