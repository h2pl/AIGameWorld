"""World 状态路由 / World state routes."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.deps import get_db
from src.config import load_config
from src.repository.actor_repo import ActorRepo
from src.repository.item_repo import ItemRepo
from src.repository.pc_repo import PcRepo
from src.repository.scene_repo import SceneRepo
from src.repository.world_repo import WorldRepo

router = APIRouter(prefix="/api/world", tags=["state"])


def _char_from_row(r: dict, is_pc: bool, pos_offset: int) -> dict:
    cj = r.get("combat_json")
    return {
        "id": r["id"],
        "name": r["name"],
        "role": r["role"],
        "race": r.get("race"),
        "status": r.get("status", "active"),
        "scene_id": r["scene_id"],
        "position_x": r.get("position_x", pos_offset),
        "position_y": r.get("position_y", 5 + pos_offset % 10),
        "attributes": json.loads(r["attributes_json"]),
        "combat": json.loads(cj) if cj else None,
        "personality": r.get("personality", ""),
        "arc": json.loads(r.get("arc_json", "{}")) if is_pc else None,
        "functions": json.loads(r.get("functions_json", "[]")) if not is_pc else None,
        "is_pc": is_pc,
    }


@router.get("/{world_id}/state")
async def get_pack_state(world_id: str, request: Request, db=Depends(get_db)):
    """获取世界初始状态（场景、角色、物品、物体）/ Get initial world state."""
    try:
        scene_repo = SceneRepo(db)
        pc_repo = PcRepo(db)
        actor_repo = ActorRepo(db)
        item_repo = ItemRepo(db)
        world_repo = WorldRepo(db)

        # 场景 / Scenes
        scenes = await scene_repo.list_scenes(world_id)

        # PC / Player characters
        pcs = [
            _char_from_row(r, True, i * 2 + 5)
            for i, r in enumerate(await pc_repo.list_rows(world_id))
        ]
        # NPC / Actors
        actors = [
            _char_from_row(r, False, i * 3 + 12)
            for i, r in enumerate(await actor_repo.list_rows(world_id))
        ]

        # 物品 / Items
        items = await item_repo.list_by_world(world_id)

        # 场景物体 / Scene objects
        scene_objects = await scene_repo.list_objects_by_world(world_id)

        # 世界 tick / World ticks
        data_tick = await world_repo.get_data_tick(world_id)
        display_tick = await world_repo.get_display_tick(world_id)

        cfg = load_config(os.environ.get("AIGW_CONFIG", "../config.yaml"))
        db_name = Path(cfg.db_name).name

        return {
            "world_id": world_id,
            "trace_id": getattr(request.state, "trace_id", ""),
            "data_tick": data_tick,
            "display_tick": display_tick,
            "llm_mock": cfg.llm_mock,
            "data_mode": cfg.data_mode,
            "db_name": db_name,
            "runtime": {"llm_mock": cfg.llm_mock, "data_mode": cfg.data_mode, "db_name": db_name},
            "scenes": scenes,
            "pcs": pcs,
            "actors": actors,
            "items": items,
            "scene_objects": scene_objects,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="DB unavailable") from exc
