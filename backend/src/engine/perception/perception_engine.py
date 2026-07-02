"""Character Perception Engine——组装每个角色的感知上下文."""

import logging

from langchain_core.runnables.config import RunnableConfig

from ...utils.helpers import get_repo

# 模块日志 / Module logger
logger = logging.getLogger("aw.eng.char")


async def perceive_characters(
    world_id: str,
    tick: int,
    scene_id: str,
    plot_brief: str,
    hints: list[str],
    config: RunnableConfig = None,
) -> list[dict]:
    """组装每个角色的感知上下文 / Build per-character perceived contexts."""
    # 角色、场景、记忆仓储 / Character, scene, and memory repositories
    char_repo = get_repo(config, "char")
    scene_repo = get_repo(config, "scene")
    memory_repo = get_repo(config, "memory")
    if not char_repo:
        logger.warning("[character] no char_repo, skip perceive")
        return []

    pcs = await char_repo.load_pcs(world_id) if world_id else []
    actors = await char_repo.load_actors(world_id) if world_id else []
    all_chars = [("pc", pc) for pc in pcs] + [("actor", actor) for actor in actors]

    # 当前场景物体 / Scene objects in current scene
    scene_objects = []
    if scene_repo and scene_id:
        object_ids = await scene_repo.get_object_ids(scene_id)
        all_objects = await scene_repo.load_all()
        scene_objects = [
            {
                "object_id": oid,
                "name": all_objects[oid].name,
                "object_type": all_objects[oid].object_type.value,
                "position_x": all_objects[oid].position_x,
                "position_y": all_objects[oid].position_y,
            }
            for oid in object_ids
            if oid in all_objects
        ]

    # 为每个角色生成局部观察结果 / Build local observations per character
    contexts: list[dict] = []
    for char_type, char in all_chars:
        if getattr(char, "scene_id", "") != scene_id:
            continue
        visible_characters = [
            {
                "character_id": other.id,
                "character_type": other_type,
                "name": other.name,
                "role": getattr(other, "role", ""),
                "scene_id": getattr(other, "scene_id", ""),
            }
            for other_type, other in all_chars
            if other.id != char.id and getattr(other, "scene_id", "") == scene_id
        ]
        recent_memories = []
        if memory_repo:
            recent_memories = [
                {"content": mem.content, "tick": mem.tick, "importance": mem.importance}
                for mem in list(memory_repo._short_queue(char.id))[-5:]
            ]
            observation = f"Tick {tick}: 在场景 {scene_id} 观察到 {len(visible_characters)} 名角色与 {len(scene_objects)} 个物体。"
            memory_repo.store(char.id, observation, tick, importance=2)

        contexts.append(
            {
                "character_id": char.id,
                "character_type": char_type,
                "scene_id": scene_id,
                "plot_brief": plot_brief,
                "hints": hints,
                "self_state": {
                    "name": char.name,
                    "role": getattr(char, "role", ""),
                    "status": getattr(char, "status", ""),
                    "position_x": getattr(char, "position_x", 0),
                    "position_y": getattr(char, "position_y", 0),
                },
                "visible_characters": visible_characters,
                "visible_objects": scene_objects,
                "recent_memories": recent_memories,
            }
        )

    return contexts
