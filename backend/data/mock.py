"""Mock 数据生成器 / Mock data generator.

为所有业务表生成一套合理的 mock 数据，用于前端展示和测试。
不依赖 world-pack，通过 repo 层灌入 SQLite，保持与生产代码一致。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 允许从 backend/data 导入 src 模块 / Allow importing src modules from backend/data
_BACKEND_ROOT = Path(__file__).parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from src.domain import (  # noqa: E402
    Actor,
    Item,
    ItemType,
    PlayerCharacter,
    SceneObject,
    SceneObjectType,
)
from src.domain.world import World  # noqa: E402
from src.repository.actor_repo import ActorRepo  # noqa: E402
from src.repository.item_repo import ItemRepo  # noqa: E402
from src.repository.pc_repo import PcRepo  # noqa: E402
from src.repository.scene_repo import SceneRepo  # noqa: E402
from src.repository.world_repo import WorldRepo  # noqa: E402

MOCK_WORLD_ID = "mock_world"
MOCK_WORLD_NAME = "Mock World"


def now() -> str:
    """当前 UTC 时间字符串 / Current UTC time string."""
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def _j(data: Any) -> str:
    """JSON 序列化辅助 / JSON serialization helper."""
    return json.dumps(data, ensure_ascii=False)


async def seed_mock_data(db: Any, world_id: str = MOCK_WORLD_ID) -> None:
    """向数据库灌入全套 mock 数据 / Seed full mock data into DB.

    幂等处理：先清空该 world 下所有业务数据，再重新插入，
    避免后端重启或 reset 后因主键冲突导致角色/场景未注入。
    """
    # 幂等：先清理旧数据 / Idempotent: clear old data first
    world_repo = WorldRepo(db)
    scene_repo = SceneRepo(db)
    pc_repo = PcRepo(db)
    actor_repo = ActorRepo(db)
    item_repo = ItemRepo(db)

    await pc_repo.delete_by_world(world_id)
    await actor_repo.delete_by_world(world_id)
    await scene_repo.delete_by_world(world_id)
    await item_repo.delete_by_world(world_id)
    await world_repo.delete(world_id)

    await _seed_world(world_repo, world_id)
    await _seed_scenes(scene_repo, world_id)
    await _seed_items(item_repo, world_id)
    await _seed_scene_objects(scene_repo, world_id)
    await _seed_pcs(pc_repo, world_id)
    await _seed_actors(actor_repo, world_id)


async def _seed_world(world_repo: WorldRepo, world_id: str) -> None:
    """灌入 world 记录 / Seed world record."""
    await world_repo.create(
        World(
            id=world_id,
            name=MOCK_WORLD_NAME,
            description="一个用于前端展示和测试的 mock 世界。",
            version="1.0.0",
            rule_set="dnd_5e_srd",
            author="AIGameWorld",
            data_tick=0,
            display_tick=0,
        )
    )


async def _seed_scenes(scene_repo: SceneRepo, world_id: str) -> None:
    """灌入场景 / Seed scenes."""
    scenes = [
        {
            "id": "village_elderwood",
            "name": "Elderwood Village",
            "type": "village",
            "description": "A quiet border village, smoke rising from the blacksmith's chimney.",
            "map_key": "tuxemon-map",
            "spawn_x": 20,
            "spawn_y": 20,
            "map_width": 40,
            "map_height": 40,
            "ext_json": '{"tilemap_url":"/assets/tuxemon-town.json","tileset_url":"/assets/rpg_tileset.png","tileset_name":"tuxemon-sample-32px-extruded","tileset_image_key":"tuxemon"}',
        },
        {
            "id": "desert",
            "name": "Scorching Desert",
            "type": "outdoor",
            "description": "An endless sea of sand under the blazing sun.",
            "map_key": "desert-map",
            "spawn_x": 10,
            "spawn_y": 10,
            "map_width": 40,
            "map_height": 40,
            "ext_json": '{"tilemap_url":"/assets/desert.json","tileset_url":"/assets/tmw_desert_spacing.png","tileset_name":"Desert","tileset_image_key":"desert-tiles"}',
        },
    ]
    for s in scenes:
        await scene_repo.save_scene(s, world_id)


async def _seed_items(item_repo: ItemRepo, world_id: str) -> None:
    """灌入全局物品 / Seed global items."""
    items = [
        {
            "id": "longsword",
            "name": "Longsword",
            "item_type": ItemType.WEAPON,
            "rarity": "common",
            "description": "一把标准长剑。",
        },
        {
            "id": "shortsword",
            "name": "Shortsword",
            "item_type": ItemType.WEAPON,
            "rarity": "common",
            "description": "轻便的短剑。",
        },
        {
            "id": "mace",
            "name": "Mace",
            "item_type": ItemType.WEAPON,
            "rarity": "common",
            "description": "钝器，对重甲有效。",
        },
        {
            "id": "staff",
            "name": "Staff",
            "item_type": ItemType.WEAPON,
            "rarity": "common",
            "description": "施法者的木杖。",
        },
        {
            "id": "war_hammer",
            "name": "War Hammer",
            "item_type": ItemType.WEAPON,
            "rarity": "common",
            "description": "矮人铁匠喜爱的重锤。",
        },
        {
            "id": "leather_armor",
            "name": "Leather Armor",
            "item_type": ItemType.ARMOR,
            "rarity": "common",
            "description": "柔韧的皮甲。",
        },
        {
            "id": "chain_mail",
            "name": "Chain Mail",
            "item_type": ItemType.ARMOR,
            "rarity": "common",
            "description": "锁子甲，防护更好。",
        },
        {
            "id": "shield",
            "name": "Shield",
            "item_type": ItemType.SHIELD,
            "rarity": "common",
            "description": "木制圆盾。",
        },
        {
            "id": "health_potion",
            "name": "Health Potion",
            "item_type": ItemType.POTION,
            "rarity": "common",
            "description": "回复少量生命。",
        },
        {
            "id": "rusty_key",
            "name": "Rusty Key",
            "item_type": ItemType.KEY,
            "rarity": "uncommon",
            "description": "一把生锈的钥匙，能打开某扇门。",
        },
    ]
    for it in items:
        await item_repo.save(
            Item(
                id=it["id"],
                name=it["name"],
                item_type=it["item_type"],
                rarity=it["rarity"],
                description=it["description"],
                world_id=world_id,
            )
        )


async def _seed_scene_objects(scene_repo: SceneRepo, world_id: str) -> None:
    """灌入场景物体 / Seed scene objects."""
    objects = [
        SceneObject(
            id="chest_wooden",
            name="Wooden Chest",
            object_type=SceneObjectType.CONTAINER,
            scene_id="village_elderwood",
            position_x=16,
            position_y=16,
            world_id=world_id,
        ),
        SceneObject(
            id="door_cellar",
            name="Cellar Door",
            object_type=SceneObjectType.DOOR,
            scene_id="village_elderwood",
            position_x=24,
            position_y=20,
            world_id=world_id,
        ),
    ]
    for obj in objects:
        await scene_repo.save_object(obj)


async def _seed_pcs(pc_repo: PcRepo, world_id: str) -> None:
    """灌入玩家角色 / Seed player characters.

    初始坐标全部设为 (0,0)，由前端 setWorldState 根据 scene spawn 自动分配，
    避免角色堆叠在一起。
    """
    pcs = [
        {
            "id": "cleric",
            "name": "Cleric",
            "role": "cleric",
            "race": "elf",
            "attributes": {
                "strength": 12,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 12,
                "wisdom": 18,
                "charisma": 14,
            },
            "combat": {
                "hp": 28,
                "max_hp": 28,
                "ac": 14,
                "initiative": 0,
                "speed": 30,
                "attack_bonus": 4,
                "damage_dice": "1d4",
            },
            "personality": "虔诚、温和，但在面对邪恶时毫不退缩。",
            "equipment": {"weapon": "longsword", "armor": "leather_armor"},
        },
        {
            "id": "fighter",
            "name": "Fighter",
            "role": "fighter",
            "race": "human",
            "attributes": {
                "strength": 16,
                "dexterity": 12,
                "constitution": 16,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 12,
            },
            "combat": {
                "hp": 32,
                "max_hp": 32,
                "ac": 16,
                "initiative": 1,
                "speed": 30,
                "attack_bonus": 5,
                "damage_dice": "1d4",
            },
            "personality": "直率、勇敢，习惯于站在队伍最前面。",
            "equipment": {"weapon": "longsword", "armor": "chain_mail"},
        },
        {
            "id": "rogue",
            "name": "Rogue",
            "role": "rogue",
            "race": "human",
            "attributes": {
                "strength": 10,
                "dexterity": 18,
                "constitution": 12,
                "intelligence": 14,
                "wisdom": 10,
                "charisma": 14,
            },
            "combat": {
                "hp": 24,
                "max_hp": 24,
                "ac": 14,
                "initiative": 4,
                "speed": 30,
                "attack_bonus": 6,
                "damage_dice": "1d4",
            },
            "personality": "机敏、多疑，总能发现别人忽略的细节。",
            "equipment": {"weapon": "shortsword", "armor": "leather_armor"},
        },
        {
            "id": "wizard",
            "name": "Wizard",
            "role": "wizard",
            "race": "elf",
            "attributes": {
                "strength": 8,
                "dexterity": 12,
                "constitution": 12,
                "intelligence": 18,
                "wisdom": 14,
                "charisma": 10,
            },
            "combat": {
                "hp": 22,
                "max_hp": 22,
                "ac": 12,
                "initiative": 1,
                "speed": 30,
                "attack_bonus": 4,
                "damage_dice": "1d4",
            },
            "personality": "好奇、理性，沉迷于古老的知识。",
            "equipment": {"weapon": "staff", "armor": "leather_armor"},
        },
    ]
    for pc in pcs:
        await pc_repo.save(
            PlayerCharacter(
                id=pc["id"],
                name=pc["name"],
                role=pc["role"],
                race=pc["race"],
                status="active",
                scene_id="village_elderwood",
                position_x=0,
                position_y=0,
                attributes_json=_j(pc["attributes"]),
                combat_json=_j(pc["combat"]),
                personality=pc["personality"],
                equipment_json=_j(pc["equipment"]),
                inventory_json=_j([{"item": "health_potion", "qty": 1}]),
                world_id=world_id,
            )
        )


async def _seed_actors(actor_repo: ActorRepo, world_id: str) -> None:
    """灌入 NPC / Seed actors.

    包含友好 NPC、小怪与 Boss，放置在不同场景。
    """
    actors = [
        # --- Elderwood Village 友好 NPC ---
        {
            "id": "blacksmith",
            "name": "Blacksmith",
            "role": "blacksmith",
            "race": "dwarf",
            "disposition": "neutral",
            "scene_id": "village_elderwood",
            "x": 15,
            "y": 17,
            "attributes": {
                "strength": 16,
                "dexterity": 10,
                "constitution": 16,
                "intelligence": 10,
                "wisdom": 12,
                "charisma": 8,
            },
            "combat": {"hp": 30, "max_hp": 30, "ac": 15, "attack_bonus": 5, "damage_dice": "1d8+2"},
            "personality": "Hardworking, quiet, wary of strangers",
            "functions": ["merchant", "dialogue"],
        },
        {
            "id": "guard",
            "name": "Guard",
            "role": "guard",
            "race": "human",
            "disposition": "friendly",
            "scene_id": "village_elderwood",
            "x": 22,
            "y": 18,
            "attributes": {
                "strength": 14,
                "dexterity": 12,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 10,
            },
            "combat": {"hp": 25, "max_hp": 25, "ac": 16, "attack_bonus": 4, "damage_dice": "1d6+2"},
            "personality": "尽职、警觉，对陌生人保持礼貌但警惕。",
            "functions": ["ally"],
        },
        {
            "id": "merchant",
            "name": "Merchant",
            "role": "merchant",
            "race": "human",
            "disposition": "neutral",
            "scene_id": "village_elderwood",
            "x": 26,
            "y": 20,
            "attributes": {
                "strength": 8,
                "dexterity": 10,
                "constitution": 10,
                "intelligence": 14,
                "wisdom": 12,
                "charisma": 16,
            },
            "combat": {"hp": 18, "max_hp": 18, "ac": 10, "attack_bonus": 2, "damage_dice": "1d4+1"},
            "personality": "圆滑、健谈，任何信息都有价格。",
            "functions": ["merchant", "dialogue"],
        },
        # --- Elderwood Village 敌对生物：小怪 ---
        {
            "id": "goblin",
            "name": "Goblin",
            "role": "goblin",
            "race": "goblinoid",
            "disposition": "hostile",
            "scene_id": "village_elderwood",
            "x": 10,
            "y": 10,
            "attributes": {
                "strength": 8,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 8,
                "wisdom": 8,
                "charisma": 6,
            },
            "combat": {"hp": 7, "max_hp": 7, "ac": 12, "attack_bonus": 2, "damage_dice": "1d4+2"},
            "personality": "怯懦但贪婪，喜欢以多欺少。",
            "functions": ["enemy"],
        },
        {
            "id": "skeleton",
            "name": "Skeleton",
            "role": "skeleton",
            "race": "undead",
            "disposition": "hostile",
            "scene_id": "village_elderwood",
            "x": 30,
            "y": 10,
            "attributes": {
                "strength": 10,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 4,
                "wisdom": 8,
                "charisma": 4,
            },
            "combat": {"hp": 13, "max_hp": 13, "ac": 13, "attack_bonus": 3, "damage_dice": "1d6+1"},
            "personality": "毫无意识的不死生物，只会服从命令攻击活物。",
            "functions": ["enemy"],
        },
        # --- Elderwood Village Boss ---
        {
            "id": "orc_boss",
            "name": "Orc Warlord",
            "role": "orc_boss",
            "race": "orc",
            "disposition": "hostile",
            "scene_id": "village_elderwood",
            "x": 35,
            "y": 35,
            "attributes": {
                "strength": 18,
                "dexterity": 12,
                "constitution": 18,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 12,
            },
            "combat": {
                "hp": 45,
                "max_hp": 45,
                "ac": 15,
                "attack_bonus": 5,
                "damage_dice": "1d12+3",
            },
            "personality": "残暴好战，崇尚力量，喜欢正面碾碎敌人。",
            "functions": ["enemy", "boss"],
        },
        # --- Desert 小怪 ---
        {
            "id": "desert_scorpion",
            "name": "Giant Scorpion",
            "role": "scorpion",
            "race": "beast",
            "disposition": "hostile",
            "scene_id": "desert",
            "x": 12,
            "y": 12,
            "attributes": {
                "strength": 12,
                "dexterity": 10,
                "constitution": 12,
                "intelligence": 2,
                "wisdom": 8,
                "charisma": 4,
            },
            "combat": {"hp": 16, "max_hp": 16, "ac": 13, "attack_bonus": 3, "damage_dice": "1d8+1"},
            "personality": "潜伏在沙下的掠食者，对震动极为敏感。",
            "functions": ["enemy"],
        },
        # --- Desert Boss ---
        {
            "id": "mummy_lord",
            "name": "Mummy Lord",
            "role": "mummy_lord",
            "race": "undead",
            "disposition": "hostile",
            "scene_id": "desert",
            "x": 25,
            "y": 25,
            "attributes": {
                "strength": 16,
                "dexterity": 8,
                "constitution": 16,
                "intelligence": 10,
                "wisdom": 14,
                "charisma": 12,
            },
            "combat": {"hp": 60, "max_hp": 60, "ac": 16, "attack_bonus": 6, "damage_dice": "2d6+3"},
            "personality": "古老的沙漠统治者，怨恨所有闯入者。",
            "functions": ["enemy", "boss"],
        },
    ]
    for actor in actors:
        await actor_repo.save(
            Actor(
                id=actor["id"],
                name=actor["name"],
                role=actor["role"],
                race=actor["race"],
                status="active",
                disposition=actor["disposition"],
                scene_id=actor["scene_id"],
                position_x=actor["x"],
                position_y=actor["y"],
                attributes_json=_j(actor["attributes"]),
                combat_json=_j(actor["combat"]),
                personality=actor["personality"],
                functions_json=_j(actor["functions"]),
                function_data_json=_j({"merchant": {"gold": 500, "buyback_ratio": 0.5}}),
                equipment_json=_j({"weapon": "longsword", "armor": "leather_armor"}),
                inventory_json=_j([{"item": "longsword", "qty": 1}]),
                world_id=world_id,
            )
        )
