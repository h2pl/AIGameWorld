"""Combat Engine——战斗动作执行 / Combat action execution.

PC 移动到目标相邻格，由 LLM 直接生成战斗过程、结果与旁白，并同步更新目标状态。
不再进行任何 D20 检定或伤害计算。
"""

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

from ...domain import Actor, PlayerCharacter
from ...schemas.engine_result import CombatActionResult
from ...schemas.llm_output import CombatNarrationSchema
from ...services.memory_service import retrieve_memories
from ...utils.helpers import build_occupied_set, find_vacant_adjacent, get_llm
from ...utils.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(str(_PROMPTS_ROOT)))


async def process_combat_action(
    decision: dict,
    scene: dict[str, Any] | None = None,
    pcs: dict[str, PlayerCharacter] | None = None,
    actors: dict[str, Actor] | None = None,
    plot_brief: str = "",
    hints: list[str] | None = None,
    tick: int = 0,
    pc_memory_map: dict[str, list[dict]] | None = None,
    config: RunnableConfig = None,
) -> CombatActionResult | None:
    """处理单个 combat 决策：走位 → LLM 生成战斗 → 状态更新 → 记忆."""
    if decision.get("type") != "combat":
        return None

    pc_id = decision.get("pc_id", "")
    target_id = decision.get("target_id", "")
    target_type = decision.get("target_type", "")
    if not pc_id or not target_id:
        return None

    pc = (pcs or {}).get(pc_id)
    target = _target(target_id, target_type, pcs, actors)
    if pc is None or target is None:
        logger.warning("[combat] pc=%s or target=%s not found", pc_id, target_id)
        return None

    # 1. 走到目标旁边 / Move adjacent to target
    waypoints = _move_to_target(pc, target, pcs, actors)

    # 2. LLM 生成战斗过程、结果与旁白 / LLM generates combat narration and result
    narration_result = await _generate_narration(
        pc=pc,
        target=target,
        scene=scene or {},
        plot_brief=plot_brief,
        hints=hints or [],
        tick=tick,
        pc_memory_map=pc_memory_map,
        config=config,
    )

    # 3. 以 LLM 判断为准更新目标状态 / Update target state based on LLM outcome
    target_defeated = narration_result.target_defeated
    if target_defeated:
        _defeat(target)

    narration = narration_result.narration
    result_text = narration_result.result or ("目标被击败" if target_defeated else "双方仍在僵持")

    # 4. 写入记忆 / Stage memory
    _store_combat_memory(pc_id, target_id, target_type, narration, tick, pc_memory_map)

    logger.info(
        "[combat] %s → %s : %s (defeated=%s)",
        pc_id,
        target_id,
        narration[:30] if narration else "无旁白",
        target_defeated,
    )
    return CombatActionResult(
        pc_id=pc_id,
        target_id=target_id,
        target_type=target_type,
        waypoints=waypoints,
        narration=narration,
        combat_log=[],
        winner="party" if target_defeated else None,
        target_defeated=target_defeated,
        result=result_text,
    )


def _target(
    target_id: str,
    target_type: str,
    pcs: dict[str, PlayerCharacter] | None,
    actors: dict[str, Actor] | None,
) -> PlayerCharacter | Actor | None:
    """按类型从领域模型 map 中取目标."""
    if target_type == "pc":
        return (pcs or {}).get(target_id)
    return (actors or {}).get(target_id)


def _move_to_target(
    pc: PlayerCharacter,
    target: PlayerCharacter | Actor,
    pcs: dict[str, PlayerCharacter] | None,
    actors: dict[str, Actor] | None,
) -> list[dict]:
    """将 PC 移动到目标相邻格，返回 waypoints / Move PC adjacent to target."""
    tx, ty = target.position_x, target.position_y
    if tx == 0 and ty == 0:
        return []

    old_x, old_y = pc.position_x, pc.position_y
    occupied = build_occupied_set(pcs, actors, exclude_id=pc.id)
    new_x, new_y = find_vacant_adjacent(tx, ty, occupied)

    pc.position_x = new_x
    pc.position_y = new_y
    if old_x == new_x and old_y == new_y:
        return []
    return [{"x": old_x, "y": old_y}, {"x": new_x, "y": new_y}]


async def _generate_narration(
    pc: PlayerCharacter,
    target: PlayerCharacter | Actor,
    scene: dict[str, Any],
    plot_brief: str,
    hints: list[str],
    tick: int,
    pc_memory_map: dict[str, list[dict]] | None,
    config: RunnableConfig = None,
) -> CombatNarrationSchema:
    """调用 LLM 生成战斗旁白与结果 / Generate combat narration and result via LLM."""
    llm = get_llm(config)
    if llm is None:
        raise RuntimeError("[combat] LLM client not configured")

    query = f"{plot_brief} {target.name} {scene.get('description', '')}".strip()
    memories = await retrieve_memories(
        pc.id, query, config=config, top_k=5, pc_memory_map=pc_memory_map, current_tick=tick
    )

    ctx = {
        "pc": _combatant_ctx(pc),
        "target": _combatant_ctx(target),
        "scene": scene,
        "plot_brief": plot_brief,
        "hints": hints,
        "memories": memories,
    }

    system = _PROMPTS.get_template("combat/_combat_system.jinja").render(**ctx)
    prompt = _PROMPTS.get_template("combat/combat.jinja").render(**ctx)

    return await llm.call_structured(
        "combat",
        CombatNarrationSchema,
        [SystemMessage(content=system), HumanMessage(content=prompt)],
    )


def _combatant_ctx(char: PlayerCharacter | Actor | None) -> dict:
    """组装战斗角色上下文 / Build combatant context for prompt."""
    if char is None:
        return {"id": "", "name": "", "role": "", "race": ""}
    combat = _parse_json_field(getattr(char, "combat_json", "{}"))
    attrs = _parse_json_field(getattr(char, "attributes_json", "{}"))
    return {
        "id": char.id,
        "name": char.name,
        "role": getattr(char, "role", ""),
        "race": getattr(char, "race", None) or "",
        "status": getattr(char, "status", "active"),
        "hp": combat.get("hp", 10),
        "max_hp": combat.get("max_hp", combat.get("hp", 10)),
        "ac": combat.get("ac", 10),
        "attack_bonus": combat.get("attack_bonus", 0),
        "damage_dice": combat.get("damage_dice", "1d6"),
        "dexterity": attrs.get("dexterity", attrs.get("dex", 10)),
        "strength": attrs.get("strength", attrs.get("str", 10)),
    }


def _defeat(char: PlayerCharacter | Actor) -> None:
    """标记目标被击败并清空 hp / Mark character as defeated."""
    char.status = "dead"
    combat = _parse_json_field(getattr(char, "combat_json", "{}"))
    combat["hp"] = 0
    char.combat_json = json.dumps(combat, ensure_ascii=False)


def _store_combat_memory(
    pc_id: str,
    target_id: str,
    target_type: str,
    narration: str,
    tick: int,
    pc_memory_map: dict[str, list[dict]] | None,
) -> None:
    """把战斗记录写入 pc_memory_map / Stage combat memory into state."""
    if pc_memory_map is None or not narration:
        return
    target_label = target_id if target_type != "actor" else f"敌人 {target_id}"
    pc_memory_map.setdefault(pc_id, []).append(
        {
            "pc_id": pc_id,
            "content": f"与 {target_label} 战斗：{narration}",
            "tick": tick,
            "importance": 6,
            "memory_type": "combat",
            "entity_type": "pc",
        }
    )


def _parse_json_field(value: str | dict | None) -> dict:
    """安全解析 JSON 字段 / Safely parse a JSON string field."""
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
