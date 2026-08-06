"""新建完整世界路由 / Create-full-world route.

接收一个完整世界定义（world + scenes + pcs + actors + items + scene_objects），
一次性写入所有表。Skill 根据用户主题生成数据后调用此接口落库。
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_db
from src.domain import Actor, Item, PlayerCharacter, Scene, SceneObject, World
from src.repository.actor_repo import ActorRepo
from src.repository.item_repo import ItemRepo
from src.repository.pc_repo import PcRepo
from src.repository.scene_repo import SceneRepo
from src.repository.world_repo import WorldRepo
from src.utils.logging import get_logger, log_api

logger = get_logger(__name__)

router = APIRouter(prefix="/api/world", tags=["world-create"])


def _sanitize_json_field(val, default):
    """把关心的 *_json 字段规范化为合法 JSON 字符串，确保落库内容可被 json.loads 解析。

    skill（world-builder）由 LLM 生成 world 定义，LLM 可能产出不合法的 JSON 字符串
    （缺引号、未闭合、单引号键等）。此处做写入侧兜底：解析失败则回退默认空值，
    避免脏数据入库后 /state 等读取路径 json.loads 崩溃。
    """
    if val is None:
        return json.dumps(default, ensure_ascii=False)
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if not isinstance(val, str):
        return json.dumps(default, ensure_ascii=False)
    try:
        parsed = json.loads(val)
    except (json.JSONDecodeError, TypeError):
        logger.warning("[world_create] JSON 字段非法，回退默认值: %r", val[:80])
        return json.dumps(default, ensure_ascii=False)
    # 解析成功但类型与默认不符（如默认 {} 却得到 list）也归一并回退，保持一致
    if isinstance(default, dict) and not isinstance(parsed, dict):
        return json.dumps(default, ensure_ascii=False)
    if isinstance(default, list) and not isinstance(parsed, list):
        return json.dumps(default, ensure_ascii=False)
    return json.dumps(parsed, ensure_ascii=False)


def _sanitize_entity(entity, json_fields: dict[str, object]) -> None:
    """就地规范化实体的 *_json 字段 / Sanitize *_json fields of an entity in place."""
    for field, default in json_fields.items():
        if hasattr(entity, field):
            setattr(entity, field, _sanitize_json_field(getattr(entity, field), default))


# 各实体 *_json 字段与其默认空值 / *_json fields and their safe defaults
_SCENE_JSON_FIELDS = {
    "ext_json": {},
    "tilemap_summary": {},
}
_PC_JSON_FIELDS = {
    "attributes_json": {},
    "combat_json": {},
    "arc_json": {},
    "values_json": [],
    "relationships_json": {},
    "equipment_json": {},
    "inventory_json": [],
}
_ACTOR_JSON_FIELDS = {
    "attributes_json": {},
    "combat_json": {},
    "functions_json": [],
    "function_data_json": {},
    "inventory_json": [],
    "relationships_json": {},
}
_ITEM_JSON_FIELDS = {
    "data": {},
}
_OBJ_JSON_FIELDS = {
    "interact_data": {},
    "ext_json": {},
}


class WorldCreateRequest(BaseModel):
    """完整世界定义 / Full world definition.

    复用现有领域模型作为结构，skill 生成主题数据后填充。
    """

    world: World
    scenes: list[Scene] = []
    pcs: list[PlayerCharacter] = []
    actors: list[Actor] = []
    items: list[Item] = []
    scene_objects: list[SceneObject] = []


@router.post("/create")
async def world_create(req: WorldCreateRequest, db=Depends(get_db)):
    """新建一个完整世界（写入全部实体表）/ Create a full world (write all entity tables)."""
    log_api("world.create", req.world.id)
    world_id = req.world.id

    try:
        # 写入前规范化所有 *_json 字段：skill（LLM 生成）可能产出不合法 JSON 字符串，
        # 在此兜底为合法 JSON，避免脏数据入库后读取路径崩溃。
        for sc in req.scenes:
            _sanitize_entity(sc, _SCENE_JSON_FIELDS)
        for pc in req.pcs:
            _sanitize_entity(pc, _PC_JSON_FIELDS)
        for actor in req.actors:
            _sanitize_entity(actor, _ACTOR_JSON_FIELDS)
        for item in req.items:
            _sanitize_entity(item, _ITEM_JSON_FIELDS)
        for obj in req.scene_objects:
            _sanitize_entity(obj, _OBJ_JSON_FIELDS)

        # 1. 写 world / Write world
        world_repo = WorldRepo(db)
        await world_repo.create(req.world)

        # 2. 写场景 / Write scenes
        scene_repo = SceneRepo(db)
        for sc in req.scenes:
            await scene_repo.save_scene(sc, world_id)

        # 3. 写 PC / Write player characters
        pc_repo = PcRepo(db)
        for pc in req.pcs:
            await pc_repo.save(pc)

        # 4. 写 NPC / Write actors
        actor_repo = ActorRepo(db)
        for actor in req.actors:
            await actor_repo.save(actor)

        # 5. 写物品 / Write items
        item_repo = ItemRepo(db)
        for item in req.items:
            await item_repo.save(item)

        # 6. 写场景物体 / Write scene objects
        for obj in req.scene_objects:
            await scene_repo.save_object(obj)

        logger.info(
            "[world_create] world=%s scenes=%d pcs=%d actors=%d items=%d objects=%d",
            world_id,
            len(req.scenes),
            len(req.pcs),
            len(req.actors),
            len(req.items),
            len(req.scene_objects),
        )
        return {
            "status": "ok",
            "world_id": world_id,
            "counts": {
                "scenes": len(req.scenes),
                "pcs": len(req.pcs),
                "actors": len(req.actors),
                "items": len(req.items),
                "scene_objects": len(req.scene_objects),
            },
        }
    except Exception as exc:
        logger.exception("[world_create] create world %s failed", world_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
