"""新建完整世界路由 / Create-full-world route.

接收一个完整世界定义（world + scenes + pcs + actors + items + scene_objects），
一次性写入所有表。Skill 根据用户主题生成数据后调用此接口落库。
"""

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
