"""Mock 初始世界状态 / Mock initial world state — 对应前端 loadMockState()

后端真实链路 GET /api/pack/{id}/state 查 DB 返回。
mock 模式直接返回此数据，跳过 DB。

数据结构 / Data structure:
  scenes: 1 个村庄场景 (village_elderwood)
  characters: 4 PC (fighter/rogue/cleric/wizard) + 3 Actor (blacksmith/guard/merchant)
  items: 长剑+生命药水
  scene_objects: 木箱+地窖门

当 config.yaml mock_mode: true 时，main.py 和 ws.py 使用此数据。
切换到真实链路: mock_mode: false，后端从 DB 加载。
"""

# ══ 场景 / Scenes ══
# 1 个村庄，含出口+地标+环境
# 出口 target_scene: "desert" 对应 desert-map

# ══ 角色 / Characters ══
# 4 PC (fighter/rogue/cleric/wizard) + 3 Actor (blacksmith/guard/merchant)
# 坐标均落在 40x40 tile 范围内，前端 calcSteps 计算行走路径

# ══ 物品与场景物品 / Items & Scene Objects ══
# 长剑+生命药水 + 木箱+地窖门
# 注意: 物品在前端不可点击，场景物品(ObjectPanel)可点击查看
# 场景物品的 texture 由 GameScene.createTerrain() 根据 object_type 动态生成
# 修改数据后无需重启前端，Vite HMR 会自动刷新

MOCK_WORLD = {
    "world_id": "forgotten_realms",  # 对应 Worlds/forgotten_realms 目录
    "scenes": [
        {
            "id": "village_elderwood",
            "name": "Elderwood Village",
            "type": "village",
            "description": "A quiet border village, smoke rising from the blacksmith's chimney.",
            "exits": [
                {
                    "target_scene": "desert",
                    "position": {"x": 28, "y": 0},
                    "description": "Path to the northern desert",
                }
            ],
            "landmarks": [
                {"id": "blacksmith_shop", "name": "Blacksmith", "position": {"x": 5, "y": 7}},
                {"id": "tavern", "name": "Tavern", "position": {"x": 15, "y": 3}},
                {"id": "market", "name": "Market", "position": {"x": 12, "y": 10}},
            ],
            "environment": {"weather": "clear", "time_of_day": "morning"},
        }
    ],
    "characters": [
        {
            "id": "fighter",
            "name": "Kael",
            "role": "fighter",
            "race": "human",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 6,
            "position_y": 6,
            "attributes": {
                "strength": 16,
                "dexterity": 12,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 12,
            },
            "combat": {
                "hp": 28,
                "max_hp": 28,
                "ac": 16,
                "attack_bonus": 5,
                "damage_dice": "1d8",
                "initiative": 2,
            },
            "personality": "Brave but impulsive.",
            "arc": {"stage": "growth", "description": "Prove himself"},
            "is_pc": True,
        },
        {
            "id": "rogue",
            "name": "Zeph",
            "role": "rogue",
            "race": "elf",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 14,
            "position_y": 6,
            "attributes": {
                "strength": 10,
                "dexterity": 18,
                "constitution": 12,
                "intelligence": 14,
                "wisdom": 12,
                "charisma": 14,
            },
            "combat": {
                "hp": 20,
                "max_hp": 20,
                "ac": 14,
                "attack_bonus": 6,
                "damage_dice": "1d6",
                "initiative": 4,
            },
            "personality": "Sly and curious.",
            "arc": {"stage": "crisis", "description": "Trust issues"},
            "is_pc": True,
        },
        {
            "id": "cleric",
            "name": "Elara",
            "role": "cleric",
            "race": "human",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 6,
            "position_y": 12,
            "attributes": {
                "strength": 12,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 12,
                "wisdom": 18,
                "charisma": 14,
            },
            "combat": {
                "hp": 24,
                "max_hp": 24,
                "ac": 18,
                "attack_bonus": 4,
                "damage_dice": "1d8",
                "initiative": 1,
            },
            "personality": "Calm and devout.",
            "arc": {"stage": "growth", "description": "Seeking signs"},
            "is_pc": True,
        },
        {
            "id": "wizard",
            "name": "Mira",
            "role": "wizard",
            "race": "elf",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 14,
            "position_y": 12,
            "attributes": {
                "strength": 8,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 18,
                "wisdom": 14,
                "charisma": 10,
            },
            "combat": {
                "hp": 16,
                "max_hp": 16,
                "ac": 12,
                "attack_bonus": 3,
                "damage_dice": "1d6",
                "initiative": 2,
            },
            "personality": "Brilliant but aloof.",
            "arc": {"stage": "setup", "description": "Uncover ancient lore"},
            "is_pc": True,
        },
        {
            "id": "blacksmith",
            "name": "Garret",
            "role": "blacksmith",
            "race": "dwarf",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 4,
            "position_y": 8,
            "attributes": {
                "strength": 14,
                "dexterity": 10,
                "constitution": 16,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 10,
            },
            "combat": None,
            "personality": "Gruff but kind.",
            "functions": ["merchant"],
            "is_pc": False,
        },
        {
            "id": "guard",
            "name": "Borin",
            "role": "guard",
            "race": "human",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 10,
            "position_y": 2,
            "attributes": {
                "strength": 14,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 12,
                "charisma": 10,
            },
            "combat": {
                "hp": 22,
                "max_hp": 22,
                "ac": 15,
                "attack_bonus": 4,
                "damage_dice": "1d8",
                "initiative": 1,
            },
            "personality": "Stern but fair.",
            "functions": ["guard"],
            "is_pc": False,
        },
        {
            "id": "merchant",
            "name": "Selia",
            "role": "merchant",
            "race": "human",
            "status": "active",
            "scene_id": "village_elderwood",
            "position_x": 24,
            "position_y": 8,
            "attributes": {
                "strength": 8,
                "dexterity": 12,
                "constitution": 10,
                "intelligence": 14,
                "wisdom": 12,
                "charisma": 16,
            },
            "combat": None,
            "personality": "Charming and shrewd.",
            "functions": ["merchant"],
            "is_pc": False,
        },
    ],
    "items": [
        {
            "id": "longsword",
            "name": "Longsword",
            "item_type": "weapon",
            "rarity": "common",
            "description": "A well-forged blade.",
        },
        {
            "id": "health_potion",
            "name": "Health Potion",
            "item_type": "potion",
            "rarity": "common",
            "description": "Heals 2d4+2 HP.",
        },
    ],
    "scene_objects": [
        {
            "id": "chest_wooden",
            "name": "Wooden Chest",
            "object_type": "container",
            "scene_id": "village_elderwood",
            "position_x": 20,
            "position_y": 15,
        },
        {
            "id": "door_cellar",
            "name": "Cellar Door",
            "object_type": "door",
            "scene_id": "village_elderwood",
            "position_x": 25,
            "position_y": 5,
        },
    ],
}
