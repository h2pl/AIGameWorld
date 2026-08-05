"""角色身份与背景映射工具 / Character identity & background mapper.

供各 LLM 引擎（decision/talk/interact/combat/explore/party）复用，
统一注入角色的背景信息（长期目标/价值观/角色弧/人际关系/装备/物品）。
"""

import json


def map_identity(char) -> dict:
    """从领域模型读取角色身份与背景 / Read character identity + background."""
    if char is None:
        return {
            "id": "",
            "name": "",
            "role": "",
            "race": "",
            "status": "active",
            "personality": "",
            "disposition": "neutral",
            "long_term_goal": "",
            "core_values": "",
            "arc": "",
            "relationships": "",
            "equipment": "",
            "inventory": "",
        }
    return {
        "id": char.id,
        "name": char.name,
        "role": getattr(char, "role", ""),
        "race": getattr(char, "race", None) or "",
        "status": getattr(char, "status", "active"),
        "personality": getattr(char, "personality", ""),
        "disposition": getattr(char, "disposition", "neutral"),
        # 背景注入（PC 特有，Actor 缺省） / Background injection (PC-specific)
        "long_term_goal": getattr(char, "long_term_goal", "") or "",
        "core_values": _json_list(getattr(char, "values_json", None)),
        "arc": _json_dict(getattr(char, "arc_json", None)),
        "relationships": _json_dict(getattr(char, "relationships_json", None)),
        "equipment": _json_dict(getattr(char, "equipment_json", None)),
        "inventory": _json_list(getattr(char, "inventory_json", None)),
    }


def _json_dict(raw) -> str:
    """解析 JSON 字段为可读字符串 / Parse JSON field to readable string."""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and data:
            return ", ".join(f"{k}:{v}" for k, v in data.items())
        return str(data)
    except Exception:
        return str(raw)


def _json_list(raw) -> str:
    """解析 JSON 数组为可读字符串 / Parse JSON list to readable string."""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return "、".join(str(x) for x in data)
        return str(data)
    except Exception:
        return str(raw)
