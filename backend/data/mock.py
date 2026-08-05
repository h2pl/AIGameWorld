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
from src.repository.actor_repo import ActorRepo  # noqa: E402
from src.repository.item_repo import ItemRepo  # noqa: E402
from src.repository.pc_repo import PcRepo  # noqa: E402
from src.repository.scene_repo import SceneRepo  # noqa: E402

# 默认 world（兼容旧调用：seed_mock_data(db, world_id) 仍可单独灌一个世界）/
# Default world (legacy: seed_mock_data(db, world_id) still seeds one world)
MOCK_WORLD_ID = "mock_world"
MOCK_WORLD_NAME = "Mock World"


# 世界配置 / World configurations（两个主题世界）
# 场景由 gen_scene 导入的有语义地图提供，按 world_id 绑定。
WORLDS: list[dict] = [
    {
        "id": "xianjian",
        "name": "仙剑奇侠传·蜀山",
        "description": (
            "《仙剑奇侠传》世界观：神州大地六界并存（神界、仙界、魔界、人界、鬼界、妖界），"
            "人类修士通过修行感悟天地灵气，御剑飞行、呼风唤雨。蜀山剑派为天下名门正派之首，"
            "以斩妖除魔、守护苍生为己任。天地间妖魔横行，上古封印渐次松动，各方势力暗流涌动。"
            "主角团肩负着阻止妖魔为祸、揭开宿命真相的使命。"
        ),
        "version": "1.0.0",
        "rule_set": "xianxia",
        "author": "AIGameWorld",
        "starting_scene_id": "azure_town",
        # 该世界绑定的有语义场景（world_id 归属）/
        "scene_ids": ["azure_town", "spyder_cotton_tunnel"],
    },
    {
        "id": "warcraft",
        "name": "魔兽世界·艾泽拉斯",
        "description": (
            "《魔兽世界》世界观：艾泽拉斯大陆在泰坦创世后饱经战乱，燃烧军团的恶魔、亡灵天灾的瘟疫、"
            "部落与联盟的旷日战争交织在一起。矮人、兽人、人类、精灵等种族为了各自的生存与荣耀而战。"
            "上古之神在黑暗中低语，企图吞噬这个世界。主角团作为一支冒险者小队，"
            "在战火纷飞的大陆上探寻真相、对抗邪恶。"
        ),
        "version": "1.0.0",
        "rule_set": "warcraft",
        "author": "AIGameWorld",
        "starting_scene_id": "taba_town",
        "scene_ids": ["taba_town", "water_cathedral"],
    },
]


def now() -> str:
    """当前 UTC 时间字符串 / Current UTC time string."""
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def _j(data: Any) -> str:
    """JSON 序列化辅助 / JSON serialization helper."""
    return json.dumps(data, ensure_ascii=False)


async def seed_mock_data(db: Any, world_id: str = MOCK_WORLD_ID) -> None:
    """向数据库灌入全套 mock 数据 / Seed full mock data into DB.

    遍历 WORLDS 配置，为每个主题世界灌入 world + 场景绑定 + PC/NPC/场景物体。
    默认不删除已有数据（gen_scene 导入的场景保留），各 _seed_* 幂等补齐。
    world_id 参数兼容旧调用：传入时仅灌该世界；默认灌全部世界。
    """
    scene_repo = SceneRepo(db)
    pc_repo = PcRepo(db)
    actor_repo = ActorRepo(db)
    item_repo = ItemRepo(db)

    # 选择要灌入的世界 / Select worlds to seed
    worlds = [w for w in WORLDS if w["id"] == world_id] if world_id != MOCK_WORLD_ID else WORLDS
    if not worlds:
        worlds = [w for w in WORLDS if w["id"] == world_id]

    for w in worlds:
        wid = w["id"]
        await _seed_world(db, w)
        # 场景由 gen_scene 导入的有语义地图提供，这里把场景 world_id 绑定到该世界 /
        # Bind imported semantic maps to this world by updating their world_id
        await _bind_scenes(db, wid, w["scene_ids"])
        await _seed_items(item_repo, wid)
        await _seed_scene_objects(scene_repo, w)
        await _seed_pcs(pc_repo, w)
        await _seed_actors(actor_repo, w)


async def _seed_world(db: Any, w: dict) -> None:
    """灌入单个 world 记录（upsert，不删除已有数据）/ Seed one world record (upsert).

    world 的 starting_scene_id 指向该世界绑定的有语义地图，保证 world_init 能正确初始化。
    """
    await db.execute(
        "INSERT OR REPLACE INTO worlds "
        "(id, name, description, version, rule_set, author, starting_scene_id, "
        " current_scene_id, status, data_tick, display_tick, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, '', 'init', 0, 0, datetime('now', 'localtime'))",
        (
            w["id"],
            w["name"],
            w["description"],
            w["version"],
            w["rule_set"],
            w["author"],
            w["starting_scene_id"],
        ),
    )
    await db.commit()


async def _bind_scenes(db: Any, world_id: str, scene_ids: list[str]) -> None:
    """把有语义地图绑定到指定世界（更新 scene.world_id）/ Bind scenes to a world.

    场景由 gen_scene 导入，这里只更新归属，让每个世界只看到自己的场景列表。
    """
    for sid in scene_ids:
        await db.execute(
            "UPDATE scenes SET world_id = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (world_id, sid),
        )
    await db.commit()


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


async def _seed_scene_objects(scene_repo: SceneRepo, w: dict) -> None:
    """灌入场景物体（放在该世界 starting 场景）/ Seed scene objects on world starting scene."""
    world_id = w["id"]
    scene_id = w["starting_scene_id"]
    objects = [
        SceneObject(
            id=f"{world_id}_chest_wooden",
            name="Wooden Chest",
            object_type=SceneObjectType.CONTAINER,
            scene_id=scene_id,
            position_x=14,
            position_y=12,
            world_id=world_id,
        ),
        SceneObject(
            id=f"{world_id}_door_cellar",
            name="Cellar Door",
            object_type=SceneObjectType.DOOR,
            scene_id=scene_id,
            position_x=20,
            position_y=16,
            world_id=world_id,
        ),
    ]
    for obj in objects:
        await scene_repo.save_object(obj)


async def _seed_pcs(pc_repo: PcRepo, w: dict) -> None:
    """灌入该世界的玩家角色 / Seed player characters for a world.

    初始坐标设为 starting 场景 spawn 附近，避免堆叠。
    """
    world_id = w["id"]
    scene_id = w["starting_scene_id"]
    pcs = _world_pcs(w["id"])
    # 逐个写入 PC，含背景字段（长期目标/价值观/角色弧/人际关系/装备/物品）/
    # Write each PC with background fields (goal/values/arc/relationships/equipment/inventory)
    for i, pc in enumerate(pcs):
        await pc_repo.save(
            PlayerCharacter(
                id=f"{world_id}_{pc['id']}",
                name=pc["name"],
                role=pc["role"],
                race=pc["race"],
                status="active",
                scene_id=scene_id,
                position_x=8 + i * 3,
                position_y=10,
                attributes_json=_j(pc["attributes"]),
                combat_json=_j(pc["combat"]),
                personality=pc.get("personality", ""),
                long_term_goal=pc.get("long_term_goal", ""),
                values_json=_j(pc.get("values", [])),
                arc_json=_j(pc.get("arc", {})),
                relationships_json=_j(pc.get("relationships", {})),
                equipment_json=_j(pc.get("equipment", {})),
                inventory_json=_j(pc.get("inventory", [{"item": "health_potion", "qty": 1}])),
                world_id=world_id,
            )
        )


def _world_pcs(world_id: str) -> list[dict]:
    """按世界返回主题 PC 配置 / Return theme PCs per world.

    xianjian 世界为仙侠风格（剑侠/医仙/道士/刺客），warcraft 世界为奇幻风格
    （战士/圣骑士/法师/盗贼），每个 PC 含长期目标/价值观/角色弧/人际关系等背景。
    """
    if world_id == "xianjian":
        return [
            {
                "id": "swordsman",
                "name": "剑侠·云天河",
                "role": "swordsman",
                "race": "human",
                "attributes": {
                    "strength": 16,
                    "dexterity": 14,
                    "constitution": 15,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 12,
                },
                "combat": {
                    "hp": 34,
                    "max_hp": 34,
                    "ac": 16,
                    "initiative": 2,
                    "speed": 30,
                    "attack_bonus": 5,
                    "damage_dice": "1d8+2",
                },
                "personality": "剑心通明，行侠仗义，御剑斩妖，快意恩仇。",
                "long_term_goal": "追寻失落的祖传神剑，阻止魔尊破除封印，守护蜀山与人间。",
                "values": ["侠义", "守护苍生", "信守承诺"],
                "arc": "从莽撞少年成长为担当天下的剑侠",
                "relationships": {"医仙·赵灵儿": "青梅竹马", "蜀山剑尊": "授业恩师"},
                "equipment": {"weapon": "longsword", "armor": "chain_mail"},
                "inventory": [{"item": "health_potion", "qty": 2}, {"item": "御剑符", "qty": 1}],
            },
            {
                "id": "medic",
                "name": "医仙·赵灵儿",
                "role": "medic",
                "race": "elf",
                "attributes": {
                    "strength": 10,
                    "dexterity": 12,
                    "constitution": 13,
                    "intelligence": 14,
                    "wisdom": 18,
                    "charisma": 16,
                },
                "combat": {
                    "hp": 26,
                    "max_hp": 26,
                    "ac": 13,
                    "initiative": 1,
                    "speed": 30,
                    "attack_bonus": 3,
                    "damage_dice": "1d4+1",
                },
                "personality": "仙姿绰约，济世救人的医仙，能治愈伤者并感化妖魔。",
                "long_term_goal": "寻找能净化天下疫病的神药，化解人妖两界的宿怨。",
                "values": ["慈悲", "救死扶伤", "众生平等"],
                "arc": "从避世的蓬莱仙女到入世救世的医仙",
                "relationships": {"剑侠·云天河": "青梅竹马", "山野妖狐": "曾出手相救"},
                "equipment": {"weapon": "staff", "armor": "leather_armor"},
                "inventory": [{"item": "health_potion", "qty": 3}, {"item": "解毒散", "qty": 2}],
            },
            {
                "id": "taoist",
                "name": "道士·石道人",
                "role": "taoist",
                "race": "human",
                "attributes": {
                    "strength": 12,
                    "dexterity": 13,
                    "constitution": 14,
                    "intelligence": 16,
                    "wisdom": 16,
                    "charisma": 10,
                },
                "combat": {
                    "hp": 28,
                    "max_hp": 28,
                    "ac": 14,
                    "initiative": 3,
                    "speed": 30,
                    "attack_bonus": 4,
                    "damage_dice": "1d6",
                },
                "personality": "符箓咒术，通晓五行道法，深谙驱鬼辟邪之术。",
                "long_term_goal": "参透五行相生相克之道，修补上古封印，阻止妖魔重临人间。",
                "values": ["阴阳调和", "避世清修", "道法自然"],
                "arc": "从孤僻的守山道士到入世降妖的道人",
                "relationships": {"蜀山剑尊": "同门师兄弟", "魔尊·弃天": "宿敌"},
                "equipment": {"weapon": "staff", "armor": "leather_armor"},
                "inventory": [{"item": "health_potion", "qty": 1}, {"item": "符箓", "qty": 3}],
            },
            {
                "id": "assassin",
                "name": "刺客·景天",
                "role": "assassin",
                "race": "human",
                "attributes": {
                    "strength": 12,
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
                    "damage_dice": "1d4+2",
                },
                "personality": "身法灵巧，精于潜行与暗器，能发现常人所不及的线索。",
                "long_term_goal": "追查师父当年惨死的真相，找出潜藏在各派的卧底。",
                "values": ["忠诚", "恩怨分明", "明察秋毫"],
                "arc": "从孤狼刺客到融入团队的可靠伙伴",
                "relationships": {"剑侠·云天河": "生死之交", "道士·石道人": "互相试探"},
                "equipment": {"weapon": "shortsword", "armor": "leather_armor"},
                "inventory": [{"item": "health_potion", "qty": 1}, {"item": "暗器", "qty": 5}],
            },
        ]
    # warcraft（默认）
    return [
        {
            "id": "warrior",
            "name": "战士·萨姆",
            "role": "warrior",
            "race": "orc",
            "attributes": {
                "strength": 18,
                "dexterity": 12,
                "constitution": 18,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 12,
            },
            "combat": {
                "hp": 40,
                "max_hp": 40,
                "ac": 18,
                "initiative": 1,
                "speed": 30,
                "attack_bonus": 6,
                "damage_dice": "1d12+3",
            },
            "personality": "勇猛无畏的部落战士，手持巨斧为荣耀而战。",
            "long_term_goal": "为部落赢得荣耀，在艾泽拉斯的战火中证明兽人不是嗜血蛮族。",
            "values": ["荣耀", "部落至上", "战场荣誉"],
            "arc": "从渴望战斗的兽人战士到为和平而战的英雄",
            "relationships": {
                "圣骑士·阿德里安": "战场上的对手也是朋友",
                "巫妖王·奈克": "不共戴天之敌",
            },
            "equipment": {"weapon": "war_hammer", "armor": "chain_mail"},
            "inventory": [{"item": "health_potion", "qty": 2}, {"item": "大块肉干", "qty": 1}],
        },
        {
            "id": "paladin",
            "name": "圣骑士·阿德里安",
            "role": "paladin",
            "race": "human",
            "attributes": {
                "strength": 15,
                "dexterity": 10,
                "constitution": 16,
                "intelligence": 12,
                "wisdom": 14,
                "charisma": 16,
            },
            "combat": {
                "hp": 32,
                "max_hp": 32,
                "ac": 18,
                "initiative": 0,
                "speed": 30,
                "attack_bonus": 5,
                "damage_dice": "1d8+2",
            },
            "personality": "虔诚的圣光骑士，守护弱者，惩戒邪恶。",
            "long_term_goal": "净化被亡灵天灾腐化的土地，为死去的同胞讨回公道。",
            "values": ["圣光", "守护", "正义"],
            "arc": "从坚守圣光的理想骑士到直面黑暗的现实战士",
            "relationships": {"战士·萨姆": "战场上的对手也是朋友", "法师·莉娜": "并肩作战的战友"},
            "equipment": {"weapon": "mace", "armor": "chain_mail"},
            "inventory": [{"item": "health_potion", "qty": 2}, {"item": "圣水", "qty": 1}],
        },
        {
            "id": "mage",
            "name": "法师·莉娜",
            "role": "mage",
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
            "personality": "博学的奥术法师，掌握元素魔法与传送术。",
            "long_term_goal": "钻研失落的泰坦知识，理解燃烧军团的真面目，阻止恶魔入侵。",
            "values": ["知识", "理性", "探索真相"],
            "arc": "从书斋中的学者到身赴前线的奥术师",
            "relationships": {"圣骑士·阿德里安": "并肩作战的战友", "铁匠·铁锤": "经常讨教装备"},
            "equipment": {"weapon": "staff", "armor": "leather_armor"},
            "inventory": [{"item": "health_potion", "qty": 1}, {"item": "法术卷轴", "qty": 2}],
        },
        {
            "id": "rogue",
            "name": "盗贼·维恩",
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
                "damage_dice": "1d4+2",
            },
            "personality": "身手敏捷的潜行者，擅长开锁、潜行与致命一击。",
            "long_term_goal": "洗清被栽赃的罪名，揪出潜藏在城镇里的间谍。",
            "values": ["自由", "精明", "以牙还牙"],
            "arc": "从被追捕的嫌犯到揭露真相的关键人物",
            "relationships": {
                "战士·萨姆": "愿意相信他的粗豪汉子",
                "城卫兵": "曾经追捕他，如今相互猜疑",
            },
            "equipment": {"weapon": "shortsword", "armor": "leather_armor"},
            "inventory": [{"item": "health_potion", "qty": 1}, {"item": "开锁工具", "qty": 1}],
        },
    ]


async def _seed_actors(actor_repo: ActorRepo, w: dict) -> None:
    """灌入该世界的 NPC（分布在绑定场景）/ Seed actors for a world."""
    world_id = w["id"]
    actors = _world_actors(w["id"], w["starting_scene_id"], w["scene_ids"])
    # 逐个写入 NPC，scene_id 由主题配置决定（starting 场景或第二场景）/
    # Write each NPC; scene_id comes from theme config (starting or second scene)
    for actor in actors:
        await actor_repo.save(
            Actor(
                id=f"{world_id}_{actor['id']}",
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


def _world_actors(world_id: str, starting_scene: str, scene_ids: list[str]) -> list[dict]:
    """按世界返回主题 NPC 配置（分布在绑定场景）/ Return theme NPCs per world.

    友好 NPC 放 starting 场景，敌人/Boss 放第二场景（scene_ids[1]），按主题风格命名。
    """
    if world_id == "xianjian":
        return [
            {
                "id": "sword_elder",
                "name": "蜀山剑尊",
                "role": "sword_elder",
                "race": "human",
                "disposition": "friendly",
                "scene_id": starting_scene,
                "x": 15,
                "y": 17,
                "attributes": {
                    "strength": 16,
                    "dexterity": 14,
                    "constitution": 15,
                    "intelligence": 14,
                    "wisdom": 16,
                    "charisma": 14,
                },
                "combat": {
                    "hp": 45,
                    "max_hp": 45,
                    "ac": 16,
                    "attack_bonus": 7,
                    "damage_dice": "1d10+3",
                },
                "personality": "蜀山剑派长老，剑术通神，洞察妖魔。",
                "functions": ["dialogue"],
            },
            {
                "id": "medicine_immortal",
                "name": "蓬莱药仙",
                "role": "medicine_immortal",
                "race": "elf",
                "disposition": "friendly",
                "scene_id": starting_scene,
                "x": 22,
                "y": 18,
                "attributes": {
                    "strength": 8,
                    "dexterity": 12,
                    "constitution": 12,
                    "intelligence": 16,
                    "wisdom": 18,
                    "charisma": 14,
                },
                "combat": {
                    "hp": 28,
                    "max_hp": 28,
                    "ac": 12,
                    "attack_bonus": 3,
                    "damage_dice": "1d4",
                },
                "personality": "精通仙药与丹术，能医治百病。",
                "functions": ["merchant", "dialogue"],
            },
            {
                "id": "demon",
                "name": "山野妖狐",
                "role": "demon",
                "race": "beast",
                "disposition": "hostile",
                "scene_id": scene_ids[1] if len(scene_ids) > 1 else starting_scene,
                "x": 20,
                "y": 10,
                "attributes": {
                    "strength": 10,
                    "dexterity": 16,
                    "constitution": 12,
                    "intelligence": 10,
                    "wisdom": 12,
                    "charisma": 10,
                },
                "combat": {
                    "hp": 18,
                    "max_hp": 18,
                    "ac": 13,
                    "attack_bonus": 4,
                    "damage_dice": "1d6+2",
                },
                "personality": "修炼成精的狐妖，狡诈危险。",
                "functions": ["enemy"],
            },
            {
                "id": "demon_king",
                "name": "魔尊·弃天",
                "role": "demon_king",
                "race": "demon",
                "disposition": "hostile",
                "scene_id": scene_ids[1] if len(scene_ids) > 1 else starting_scene,
                "x": 30,
                "y": 30,
                "attributes": {
                    "strength": 20,
                    "dexterity": 14,
                    "constitution": 20,
                    "intelligence": 12,
                    "wisdom": 12,
                    "charisma": 16,
                },
                "combat": {
                    "hp": 70,
                    "max_hp": 70,
                    "ac": 17,
                    "attack_bonus": 8,
                    "damage_dice": "2d8+4",
                },
                "personality": "魔界至尊，欲破除上古封印，为祸苍生。",
                "functions": ["enemy", "boss"],
            },
        ]
    # warcraft（默认）
    return [
        {
            "id": "blacksmith",
            "name": "铁匠·铁锤",
            "role": "blacksmith",
            "race": "dwarf",
            "disposition": "neutral",
            "scene_id": starting_scene,
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
            "personality": "矮人铁匠，打造精良装备，消息灵通。",
            "functions": ["merchant", "dialogue"],
        },
        {
            "id": "guard",
            "name": "城卫兵",
            "role": "guard",
            "race": "human",
            "disposition": "friendly",
            "scene_id": starting_scene,
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
            "personality": "尽职尽责的城卫兵，守卫城镇安全。",
            "functions": ["ally"],
        },
        {
            "id": "undead",
            "name": "亡灵士兵",
            "role": "undead",
            "race": "undead",
            "disposition": "hostile",
            "scene_id": scene_ids[1] if len(scene_ids) > 1 else starting_scene,
            "x": 20,
            "y": 10,
            "attributes": {
                "strength": 12,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 4,
                "wisdom": 8,
                "charisma": 4,
            },
            "combat": {"hp": 15, "max_hp": 15, "ac": 12, "attack_bonus": 3, "damage_dice": "1d6+1"},
            "personality": "被亡灵天灾复生的士兵，毫无意识。",
            "functions": ["enemy"],
        },
        {
            "id": "lich",
            "name": "巫妖王·奈克",
            "role": "lich",
            "race": "undead",
            "disposition": "hostile",
            "scene_id": scene_ids[1] if len(scene_ids) > 1 else starting_scene,
            "x": 30,
            "y": 30,
            "attributes": {
                "strength": 16,
                "dexterity": 12,
                "constitution": 16,
                "intelligence": 18,
                "wisdom": 14,
                "charisma": 14,
            },
            "combat": {"hp": 65, "max_hp": 65, "ac": 16, "attack_bonus": 7, "damage_dice": "2d6+3"},
            "personality": "亡灵天灾的领袖，散播瘟疫，统领亡者军团。",
            "functions": ["enemy", "boss"],
        },
    ]
