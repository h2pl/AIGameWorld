# DB World Pack Viewer / DB 运行时数据查看器
# 路由: GET /view (选 pack + 全局入口) ｜ /view/{pack_id} (pack 详情) ｜ /view/global/* (pack 无关数据)

import contextlib
import json
from pathlib import Path

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from src.repository.character_repo import CharacterRepo
from src.repository.event_repo import EventRepo
from src.repository.item_repo import ItemRepo
from src.repository.scene_repo import SceneRepo
from src.repository.story_repo import StoryRepo
from src.repository.world_repo import WorldRepo
from src.storage.sqlite_client import SQLiteClient

_PROJECT_ROOT = Path(__file__).parent.parent  # backend/
_TEMPLATES_DIR = _PROJECT_ROOT.parent / "frontend" / "templates"  # frontend/templates/
_JINJA = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))

RARITY_COLORS = {
    "common": "#9ca3af",
    "uncommon": "#22c55e",
    "rare": "#3b82f6",
    "epic": "#a855f7",
    "legendary": "#f59e0b",
}


async def _get_client(db_path: str) -> SQLiteClient:
    client = SQLiteClient(db_path)
    await client.connect()
    return client


# ═══════════════════════════════════════════════════════════════
# Index — Pack 选择器 + 全局数据入口
# ═══════════════════════════════════════════════════════════════


async def render_index(db_path: str) -> HTMLResponse:
    if not Path(db_path).exists():
        html = _JINJA.get_template("index_db.html").render(
            packs=[], db_error=f"DB not found: {db_path}"
        )
        return HTMLResponse(html)

    client = await _get_client(db_path)
    try:
        pack_repo = WorldRepo(client)
        worlds = await pack_repo.list_all()

        # 为每个 registered pack 统计实体数
        packs = []
        for wp in worlds:
            total = 0
            _ALLOWED_TABLES = {
                "player_characters",
                "actors",
                "scenes",
                "items",
                "scene_objects",
                "story_arcs",
            }
            for table in _ALLOWED_TABLES:
                query = f"SELECT COUNT(*) as cnt FROM {table} WHERE pack_id = ?"  # noqa: S608
                row = await client.fetch_one(query, (wp.id,))
                total += row["cnt"] if row else 0
            packs.append(
                {
                    "id": wp.id,
                    "name": wp.name or wp.id,
                    "desc": wp.description,
                    "total": total,
                    "theme": getattr(wp, "theme", ""),
                    "version": wp.version,
                }
            )

        packs.sort(key=lambda p: p["total"], reverse=True)
        html = _JINJA.get_template("index_db.html").render(packs=packs, db_error=None)
    finally:
        await client.close()
    return HTMLResponse(html)


# ═══════════════════════════════════════════════════════════════
# Pack Detail — 指定 pack 的实体详情
# ═══════════════════════════════════════════════════════════════


async def render_pack(pack_id: str, db_path: str) -> HTMLResponse:
    client = await _get_client(db_path)
    try:
        char_repo = CharacterRepo(client)
        story_repo = StoryRepo(client)

        pcs = await _load_pcs(char_repo, pack_id)
        actors = await _load_actors(char_repo, pack_id)
        scenes = await _load_scenes(client, pack_id)
        items = await _load_items(client, pack_id)
        objects = await _load_objects(client, pack_id)
        arcs = await _load_arcs(story_repo, pack_id)

        html = _JINJA.get_template("pack.html").render(
            pack_id=pack_id,
            meta={"id": pack_id, "name": pack_id, "description": f"Pack: {pack_id}"},
            lore=[],
            pcs=pcs,
            actors=actors,
            items=items,
            scenes=scenes,
            objects=objects,
            story=arcs,
            rarity_colors=RARITY_COLORS,
        )
    finally:
        await client.close()
    return HTMLResponse(html)


# ═══════════════════════════════════════════════════════════════
# Global — Pack 无关数据
# ═══════════════════════════════════════════════════════════════


async def render_global_items(db_path: str) -> HTMLResponse:
    client = await _get_client(db_path)
    try:
        repo = ItemRepo(client)
        all_items = await repo.list_all()
        items = [
            {
                "id": k,
                "name": v.name,
                "item_type": v.item_type.value
                if hasattr(v.item_type, "value")
                else str(v.item_type),
                "rarity": v.rarity,
                "weight": v.weight,
                "value": v.value,
                "description": v.description,
                "pack_id": v.pack_id,
            }
            for k, v in all_items.items()
        ]
        html = _JINJA.get_template("pack.html").render(
            pack_id="global-items",
            meta={"id": "global", "name": "All Items", "description": "Pack-independent"},
            lore=[],
            pcs=[],
            actors=[],
            items=items,
            scenes=[],
            objects=[],
            story=None,
            rarity_colors=RARITY_COLORS,
        )
    finally:
        await client.close()
    return HTMLResponse(html)


async def render_global_objects(db_path: str) -> HTMLResponse:
    client = await _get_client(db_path)
    try:
        repo = SceneRepo(client)
        all_objs = await repo.list_all()
        objects = [
            {
                "id": k,
                "name": v.name,
                "object_type": v.object_type.value
                if hasattr(v.object_type, "value")
                else str(v.object_type),
                "scene_id": v.scene_id,
                "position_x": v.position_x,
                "position_y": v.position_y,
                "interactable": v.interactable,
                "interact_data": v.interact_data,
            }
            for k, v in all_objs.items()
        ]
        html = _JINJA.get_template("pack.html").render(
            pack_id="global-objects",
            meta={"id": "global", "name": "All Scene Objects", "description": "Pack-independent"},
            lore=[],
            pcs=[],
            actors=[],
            items=[],
            scenes=[],
            objects=objects,
            story=None,
            rarity_colors=RARITY_COLORS,
        )
    finally:
        await client.close()
    return HTMLResponse(html)


async def render_global_events(db_path: str) -> HTMLResponse:
    client = await _get_client(db_path)
    try:
        repo = EventRepo(client)
        events = await repo.list_all()
        html = _JINJA.get_template("events.html").render(
            events=[
                {
                    "id": e.id,
                    "tick": e.tick,
                    "type": e.type,
                    "source": e.source,
                    "target": e.target,
                    "narrative": e.narrative,
                }
                for e in events
            ],
        )
    finally:
        await client.close()
    return HTMLResponse(html)


async def render_global_narratives(db_path: str) -> HTMLResponse:
    """Narrative Log — narratives 表数据 / narratives table data."""
    client = await _get_client(db_path)
    try:
        rows = await client.fetch_all(
            "SELECT id, tick, content, created_at FROM narratives ORDER BY tick, id"
        )
        html = _JINJA.get_template("pack.html").render(
            pack_id="narratives",
            meta={
                "id": "narratives",
                "name": "Narrative Log",
                "description": "narratives 表 · 无 pack_id",
            },
            lore=[
                {
                    "category": f"Tick {r['tick']}",
                    "id": f"#{r['id']}",
                    "content": r["content"] or "",
                }
                for r in rows
            ],
            pcs=[],
            actors=[],
            items=[],
            scenes=[],
            objects=[],
            story=None,
            rarity_colors=RARITY_COLORS,
        )
    finally:
        await client.close()
    return HTMLResponse(html)


async def render_global_meta(db_path: str) -> HTMLResponse:
    """World Meta — world_meta 表 key-value / world_meta table key-value."""
    client = await _get_client(db_path)
    try:
        rows = await client.fetch_all("SELECT key, value FROM world_meta ORDER BY key")
        kv = {r["key"]: r["value"] or "" for r in rows}
        html = _JINJA.get_template("pack.html").render(
            pack_id="meta",
            meta={"id": "meta", "name": "World Meta", "description": "world_meta 运行时状态", **kv},
            lore=[],
            pcs=[],
            actors=[],
            items=[],
            scenes=[],
            objects=[],
            story=None,
            rarity_colors=RARITY_COLORS,
        )
    finally:
        await client.close()
    return HTMLResponse(html)


# ═══════════════════════════════════════════════════════════════
# 数据加载辅助 / Data load helpers (pack-filtered)
# ═══════════════════════════════════════════════════════════════


async def _load_pcs(repo: CharacterRepo, pack_id: str) -> list[dict]:
    rows = await repo._db.fetch_all(
        "SELECT id, name, role, race, scene_id, personality, attributes_json, combat_json, "
        "character_arc_json, equipment_json, inventory_json, values_json, long_term_goal "
        "FROM player_characters WHERE pack_id = ?",
        (pack_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        for k in [
            "attributes_json",
            "combat_json",
            "character_arc_json",
            "equipment_json",
            "inventory_json",
            "values_json",
        ]:
            if d.get(k):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[k.replace("_json", "")] = json.loads(d[k])
        for k in ["attributes", "combat", "character_arc", "equipment", "inventory", "values"]:
            d.setdefault(k, {} if k != "inventory" else [])
        result.append(d)
    return result


async def _load_actors(repo: CharacterRepo, pack_id: str) -> list[dict]:
    rows = await repo._db.fetch_all(
        "SELECT id, name, role, race, scene_id, personality, attributes_json, combat_json, "
        "functions_json, function_data_json, dm_assigned, motivation_injected "
        "FROM actors WHERE pack_id = ?",
        (pack_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        for k in ["attributes_json", "combat_json", "functions_json", "function_data_json"]:
            if d.get(k):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[k.replace("_json", "")] = json.loads(d[k])
        d.setdefault("attributes", {})
        d.setdefault("combat", {})
        d.setdefault("functions", [])
        d.setdefault("function_data", {})
        result.append(d)
    return result


async def _load_scenes(client: SQLiteClient, pack_id: str) -> list[dict]:
    rows = await client.fetch_all(
        "SELECT id, name, type, description, exits_json, landmarks_json, environment_json "
        "FROM scenes WHERE pack_id = ?",
        (pack_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        for k in ["exits_json", "landmarks_json", "environment_json"]:
            if d.get(k):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d[k.replace("_json", "")] = json.loads(d[k])
        result.append(d)
    return result


async def _load_items(client: SQLiteClient, pack_id: str) -> list[dict]:
    rows = await client.fetch_all(
        "SELECT id, name, item_type, rarity, weight, value, description, data_json "
        "FROM items WHERE pack_id = ?",
        (pack_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        if d.get("data_json"):
            try:
                d["data"] = json.loads(d["data_json"])
            except json.JSONDecodeError, TypeError:
                d["data"] = {}
        result.append(d)
    return result


async def _load_objects(client: SQLiteClient, pack_id: str) -> list[dict]:
    rows = await client.fetch_all(
        "SELECT id, name, object_type, scene_id, position_x, position_y, interactable, interact_data_json "
        "FROM scene_objects WHERE pack_id = ?",
        (pack_id,),
    )
    result = []
    for r in rows:
        d = dict(r)
        if d.get("interact_data_json"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                d["interact_data"] = json.loads(d["interact_data_json"])
        result.append(d)
    return result


async def _load_arcs(repo: StoryRepo, pack_id: str) -> dict | None:
    arcs = await repo.load_arcs(pack_id)
    result = [
        {
            "id": arc.id,
            "type": arc.type,
            "title": arc.title,
            "stage": arc.stage,
            "main_cast": arc.main_cast,
            "supporting_actors": arc.supporting_actors,
            "key_event_ticks": arc.key_event_ticks,
            "branching_points": arc.branching_points,
            "status": arc.status,
        }
        for arc in arcs
    ]
    return {"arcs": result} if result else None
