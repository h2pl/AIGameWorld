"""World 状态路由 / World state routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db
from src.config import load_config

# World 状态查询路由 / World state query router
router = APIRouter(prefix="/api/world", tags=["state"])


def _char_from_row(r: dict, is_pc: bool, pos_offset: int) -> dict:
    """把 DB 角色行转成前端需要的 JSON 对象 / Convert a DB character row to frontend JSON."""
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
async def get_pack_state(world_id: str, db=Depends(get_db)):
    """获取世界初始状态（场景、角色、物品、物体）/ Get initial world state."""
    try:
        # 场景列表 / Scenes in this world
        scenes = [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "description": r.get("description", ""),
                "spawn_x": r.get("spawn_x", 0),
                "spawn_y": r.get("spawn_y", 0),
            }
            for r in await db.fetch_all("SELECT * FROM scenes WHERE world_id = ?", (world_id,))
        ]
        # PC 列表 / Player characters
        pcs = [
            _char_from_row(r, True, i * 2 + 5)
            for i, r in enumerate(
                await db.fetch_all(
                    "SELECT * FROM player_characters WHERE world_id = ?", (world_id,)
                )
            )
        ]
        # NPC 列表 / Actors
        actors = [
            _char_from_row(r, False, i * 3 + 12)
            for i, r in enumerate(
                await db.fetch_all("SELECT * FROM actors WHERE world_id = ?", (world_id,))
            )
        ]
        # 全局物品 / Global items
        items = [
            {
                "id": r["id"],
                "name": r["name"],
                "item_type": r["item_type"],
                "rarity": r.get("rarity", "common"),
                "description": r.get("description", ""),
            }
            for r in await db.fetch_all("SELECT * FROM items WHERE world_id = ?", (world_id,))
        ]
        # 场景物体 / Scene objects
        so = [
            {
                "id": r["id"],
                "name": r["name"],
                "object_type": r["object_type"],
                "scene_id": r["scene_id"],
                "position_x": r.get("position_x", 0),
                "position_y": r.get("position_y", 0),
            }
            for r in await db.fetch_all(
                "SELECT * FROM scene_objects WHERE world_id = ?", (world_id,)
            )
        ]
        # 世界 tick 信息 / World tick info
        world_row = await db.fetch_one(
            "SELECT data_tick, display_tick FROM worlds WHERE id = ?", (world_id,)
        )
        data_tick = world_row["data_tick"] if world_row else 0
        display_tick = world_row["display_tick"] if world_row else 0
        # 加载配置返回 DB 名称 / Load config for DB name
        cfg = load_config("../config.yaml")
        db_path = cfg.db_name
        db_name = Path(db_path).name
        # 组装响应 / Build response
        # 运行时配置与业务状态同时存在、互不覆盖；顶层 3 个字段保留兼容旧前端
        # / Runtime config coexists with world state; top-level fields kept for backward compatibility
        return {
            "world_id": world_id,
            "data_tick": data_tick,
            "display_tick": display_tick,
            "llm_mock": cfg.llm_mock,
            "data_mode": cfg.data_mode,
            "db_name": db_name,
            "runtime": {
                "llm_mock": cfg.llm_mock,
                "data_mode": cfg.data_mode,
                "db_name": db_name,
            },
            "scenes": scenes,
            "characters": pcs + actors,
            "items": items,
            "scene_objects": so,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="DB unavailable") from exc
