"""YAML → Domain Model 反序列化 / YAML → Domain Model deserialization.

从 YAML dict 构建 Pydantic 领域模型实例。
"""

from ..domain import (
    Actor,
    Attributes,
    CharacterArc,
    CombatStats,
    Equipment,
    InventorySlot,
    Item,
    ItemType,
    Location,
    PlayerCharacter,
    SceneObject,
    SceneObjectType,
)

# ═══════════════════════════════════════════════════════════════
# 顶层实体 / Top-level entities
# ═══════════════════════════════════════════════════════════════


def pc_from_yaml(data: dict, starting_scene: str, world_id: str) -> PlayerCharacter:
    """YAML dict → PlayerCharacter."""
    return PlayerCharacter(
        id=data.get("id", ""),
        name=data.get("name", ""),
        role=data.get("role", ""),
        race=data.get("race"),
        location=Location(scene_id=data.get("scene_id") or starting_scene),
        attributes=attrs_from_yaml(data.get("attributes")),
        combat=combat_from_yaml(data.get("combat")),
        personality=data.get("personality", ""),
        character_arc=char_arc_from_yaml(data.get("character_arc")),
        long_term_goal=(data.get("character_arc") or {}).get("goal", ""),
        equipment=equip_from_yaml(data.get("equipment")),
        inventory=inventory_from_yaml(data.get("inventory")),
        world_id=world_id,
    )


def actor_from_yaml(data: dict, starting_scene: str = "", world_id: str = "") -> Actor:
    """YAML dict → Actor."""
    return Actor(
        id=data.get("id", ""),
        name=data.get("name", ""),
        role=data.get("role", ""),
        race=data.get("race"),
        location=Location(scene_id=data.get("scene_id") or starting_scene),
        attributes=attrs_from_yaml(data.get("attributes")),
        combat=combat_from_yaml(data.get("combat")),
        personality=data.get("personality", ""),
        functions=data.get("functions", []),
        function_data=data.get("function_data", {}),
        equipment=equip_from_yaml(data.get("equipment")),
        inventory=inventory_from_yaml(data.get("inventory")),
        world_id=world_id,
    )


def item_from_yaml(data: dict, world_id: str, world_name: str) -> Item:
    """YAML dict → Item."""
    return Item(
        id=data.get("id", ""),
        name=data.get("name", ""),
        item_type=ItemType(data.get("item_type", "misc")),
        rarity=data.get("rarity", "common"),
        weight=data.get("weight", 0.0),
        value=data.get("value", 0),
        description=data.get("description", ""),
        data=data.get("data", {}),
        world_id=world_id,
        world_name=world_name,
    )


def scene_obj_from_yaml(data: dict, world_id: str = "") -> SceneObject:
    """YAML dict → SceneObject."""
    return SceneObject(
        id=data.get("id", ""),
        name=data.get("name", ""),
        object_type=SceneObjectType(data.get("object_type", "decoration")),
        scene_id=data.get("scene_id", ""),
        interactable=data.get("interactable", True),
        interact_data=data.get("interact_data"),
        world_id=world_id,
    )


# ═══════════════════════════════════════════════════════════════
# 子结构 / Sub-structures
# ═══════════════════════════════════════════════════════════════


def attrs_from_yaml(data: dict | None) -> Attributes:
    if not data:
        return Attributes()
    return Attributes(
        strength=data.get("str", data.get("strength", 10)),
        dexterity=data.get("dex", data.get("dexterity", 10)),
        constitution=data.get("con", data.get("constitution", 10)),
        intelligence=data.get("int", data.get("intelligence", 10)),
        wisdom=data.get("wis", data.get("wisdom", 10)),
        charisma=data.get("cha", data.get("charisma", 10)),
    )


def combat_from_yaml(data: dict | None) -> CombatStats | None:
    if not data:
        return None
    return CombatStats(
        hp=data.get("hp", 10),
        max_hp=data.get("max_hp", data.get("hp", 10)),
        ac=data.get("ac", 10),
        initiative=data.get("initiative", 0),
        speed=data.get("speed", 30),
        attack_bonus=data.get("attack_bonus", 0),
        damage_dice=data.get("damage_dice", "1d4"),
    )


def char_arc_from_yaml(data: dict | None) -> CharacterArc:
    if not data:
        return CharacterArc()
    return CharacterArc(
        stage=data.get("stage", "setup"),
        description=data.get("description", ""),
    )


def equip_from_yaml(data: dict | None) -> Equipment:
    if not data:
        return Equipment()
    return Equipment(
        weapon_id=data.get("weapon"),
        armor_id=data.get("armor"),
        shield_id=data.get("shield"),
    )


def inventory_from_yaml(data: list | None) -> list[InventorySlot]:
    if not data:
        return []
    result: list[InventorySlot] = []
    for i in data:
        if not isinstance(i, dict):
            continue  # 跳过字符串等非 dict 项 / Skip non-dict entries
        result.append(
            InventorySlot(
                item_id=i.get("item", i.get("item_id", "")),
                quantity=i.get("qty", i.get("quantity", 1)),
            )
        )
    return result
