#!/usr/bin/env python3
"""按主题构建世界并写入 AIGameWorld / Build a themed world and write into AIGameWorld.

用法 / Usage:
    python build_world.py <world.json>            # 从 JSON 文件读取完整世界定义并写入
    python build_world.py --demo --theme "蒸汽朋克"  # 用内置模板生成演示世界并写入
    echo '{"world":...}' | python build_world.py   # 从 stdin 读取

世界定义 JSON 结构（与 POST /api/world/create 一致）:
    {
      "world": {...},
      "scenes": [...],
      "pcs": [...],
      "actors": [...],
      "items": [...],
      "scene_objects": [...]
    }
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

DEFAULT_BASE = "http://127.0.0.1:8000"


def build_demo(theme: str, name: str) -> dict:
    """根据主题生成一个演示世界 / Build a demo world from theme.

    实际使用时由 Agent 用 LLM 生成更贴合主题的数据；此模板保证接口可跑通。
    """
    # 生成 ASCII world_id（避免中文 id）：优先用 demo_ 前缀 + 简单 slug /
    # Use ASCII world_id to avoid non-ASCII ids.
    world_id = "demo_world"
    return {
        "world": {
            "id": world_id,
            "name": name or f"{theme}世界",
            "description": f"《{theme}》主题的演示世界：一个充满{theme}风格气息的奇幻大陆，正酝酿着新的冒险。",
            "version": "1.0.0",
            "rule_set": theme.lower().replace(" ", "_"),
            "author": "skill-world-builder",
            "starting_scene_id": f"{world_id}_town",
            "status": "init",
            "data_tick": 0,
            "display_tick": 0,
        },
        "scenes": [
            {
                "id": f"{world_id}_town",
                "name": f"{theme}主城",
                "type": "town",
                "description": f"这座{theme}风格的城镇是冒险者的起点，街道上人流如织。",
                "spawn_x": 9,
                "spawn_y": 10,
                "map_width": 50,
                "map_height": 50,
                "world_id": world_id,
                "tilemap_summary": json.dumps(
                    {"id": f"{world_id}_town", "type": "town", "full_interpretation": f"{theme}主城，冒险起点。"},
                    ensure_ascii=False,
                ),
                "ext_json": json.dumps({
                    "tile_size": 16,
                    "tilemap_url": "assets/tuxemon/maps/azure_town.json",
                    "tilesets": [{"name": "core_outdoor", "url": "assets/tuxemon/gfx/tilesets/core_outdoor.png"}],
                }),
            },
            {
                "id": f"{world_id}_dungeon",
                "name": f"{theme}地宫",
                "type": "indoor",
                "description": "幽深的地宫藏着这个世界的秘密与危机。",
                "spawn_x": 20,
                "spawn_y": 10,
                "map_width": 40,
                "map_height": 20,
                "world_id": world_id,
                "tilemap_summary": json.dumps(
                    {"id": f"{world_id}_dungeon", "type": "indoor", "full_interpretation": f"{theme}地宫，危机四伏。"},
                    ensure_ascii=False,
                ),
                "ext_json": json.dumps({
                    "tile_size": 16,
                    "tilemap_url": "assets/tuxemon/maps/spyder_cotton_tunnel.json",
                    "tilesets": [{"name": "core_outdoor", "url": "assets/tuxemon/gfx/tilesets/core_outdoor.png"}],
                }),
            },
        ],
        "pcs": [
            {
                "id": f"{world_id}_hero",
                "name": f"{theme}勇士",
                "role": "warrior",
                "race": "human",
                "status": "active",
                "scene_id": f"{world_id}_town",
                "position_x": 8,
                "position_y": 10,
                "attributes_json": json.dumps({"strength": 16, "dexterity": 12, "constitution": 15, "intelligence": 10, "wisdom": 10, "charisma": 12}),
                "combat_json": json.dumps({"hp": 34, "max_hp": 34, "ac": 16, "attack_bonus": 5, "damage_dice": "1d8+2"}),
                "arc_json": json.dumps({"stage": "启程", "description": "从默默无闻的冒险者到拯救世界的英雄"}),
                "long_term_goal": f"在{theme}世界闯出一番名堂，解开这个世界的谜团。",
                "values_json": json.dumps(["勇气", "正义", "荣誉"]),
                "personality": f"充满{theme}气质的勇敢冒险者。",
                "equipment_json": json.dumps({"weapon": "长剑", "armor": "皮甲"}),
                "inventory_json": json.dumps([{"item": "健康药水", "qty": 2}]),
                "relationships_json": json.dumps({}),
                "world_id": world_id,
            },
            {
                "id": f"{world_id}_mage",
                "name": f"{theme}法师",
                "role": "mage",
                "race": "elf",
                "status": "active",
                "scene_id": f"{world_id}_town",
                "position_x": 11,
                "position_y": 10,
                "attributes_json": json.dumps({"strength": 8, "dexterity": 12, "constitution": 12, "intelligence": 18, "wisdom": 14, "charisma": 10}),
                "combat_json": json.dumps({"hp": 22, "max_hp": 22, "ac": 12, "attack_bonus": 4, "damage_dice": "1d4"}),
                "arc_json": json.dumps({}),
                "long_term_goal": f"掌握{theme}世界失传的神秘力量。",
                "values_json": json.dumps(["知识", "探索"]),
                "personality": "博学而神秘，对未知充满好奇。",
                "equipment_json": json.dumps({"weapon": "法杖", "armor": "布甲"}),
                "inventory_json": json.dumps([{"item": "法力药水", "qty": 1}]),
                "relationships_json": json.dumps({}),
                "world_id": world_id,
            },
        ],
        "actors": [
            {
                "id": f"{world_id}_guard",
                "name": "城镇守卫",
                "role": "guard",
                "race": "human",
                "status": "active",
                "disposition": "friendly",
                "scene_id": f"{world_id}_town",
                "position_x": 22,
                "position_y": 18,
                "attributes_json": json.dumps({"strength": 14, "dexterity": 12, "constitution": 14, "intelligence": 10, "wisdom": 10, "charisma": 10}),
                "combat_json": json.dumps({"hp": 25, "max_hp": 25, "ac": 16, "attack_bonus": 4, "damage_dice": "1d6+2"}),
                "personality": "尽职尽责，守卫城镇安全。",
                "functions_json": json.dumps(["ally"]),
                "world_id": world_id,
            },
            {
                "id": f"{world_id}_boss",
                "name": f"{theme}魔将",
                "role": "boss",
                "race": "demon",
                "status": "active",
                "disposition": "hostile",
                "scene_id": f"{world_id}_dungeon",
                "position_x": 20,
                "position_y": 10,
                "attributes_json": json.dumps({"strength": 18, "dexterity": 12, "constitution": 18, "intelligence": 10, "wisdom": 12, "charisma": 14}),
                "combat_json": json.dumps({"hp": 65, "max_hp": 65, "ac": 16, "attack_bonus": 6, "damage_dice": "2d6+3"}),
                "personality": f"盘踞在{theme}地宫中的强大敌人。",
                "functions_json": json.dumps(["enemy", "boss"]),
                "world_id": world_id,
            },
        ],
        "items": [
            {
                "id": f"{world_id}_relic",
                "name": f"{theme}圣物",
                "item_type": "key",
                "rarity": "uncommon",
                "description": f"开启{theme}世界关键之地的圣物。",
                "world_id": world_id,
            },
        ],
        "scene_objects": [
            {
                "id": f"{world_id}_shrine",
                "name": f"{theme}祭坛",
                "object_type": "mechanism",
                "scene_id": f"{world_id}_town",
                "position_x": 14,
                "position_y": 12,
                "interactable": True,
                "world_id": world_id,
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="构建主题世界并写入 AIGameWorld")
    parser.add_argument("data", nargs="?", help="世界定义 JSON 文件路径")
    parser.add_argument("--demo", action="store_true", help="使用内置模板生成演示世界")
    parser.add_argument("--theme", default="奇幻", help="演示世界的主题")
    parser.add_argument("--name", help="演示世界的名称")
    parser.add_argument("--base", default=DEFAULT_BASE, help="后端地址")
    args = parser.parse_args()

    # 读取世界定义 / Read world definition
    if args.data:
        payload = json.loads(Path(args.data).read_text(encoding="utf-8"))
    elif args.demo:
        payload = build_demo(args.theme, args.name or f"{args.theme}·世界")
    else:
        payload = json.load(sys.stdin)

    # 调用接口 / Call the API
    resp = httpx.post(f"{args.base}/api/world/create", json=payload, timeout=60)
    if resp.status_code != 200:
        print(f"失败 / FAILED: {resp.status_code} {resp.text}", file=sys.stderr)
        return 1

    result = resp.json()
    print(f"成功 / OK: world={result['world_id']} counts={result['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
