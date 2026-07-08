"""角色 Prompt 回归测试 / Character Prompt regression tests.

验证 PC 的 System Prompt 和 Jinja 模板在变更后仍满足安全铁律和结构要求。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "src" / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


def _pc_context():
    # 构造包含场景/物体/附近角色的 prompt 上下文 / Build prompt context with scene/objects/nearby characters
    return {
        "me": {
            "id": "pc_hero",
            "name": "Hero",
            "role": "fighter",
            "race": "human",
            "status": "active",
        },
        "hints": ["注意十字路口的动静"],
        "scene": {
            "id": "crossroad",
            "name": "十字路口",
            "type": "outdoor",
            "description": "雾气弥漫的十字路口。",
        },
        "scene_objects": [
            {"id": "obj_stele", "name": "石碑", "object_type": "landmark", "interactable": True}
        ],
        "nearby_pcs": [
            {
                "id": "pc_alex",
                "name": "Alex",
                "role": "fighter",
                "race": "human",
                "status": "active",
            }
        ],
        "nearby_actors": [
            {
                "id": "npc_greta",
                "name": "Greta",
                "role": "innkeeper",
                "race": "human",
                "status": "active",
                "personality": "Warm but sharp-eyed.",
                "disposition": "neutral",
            },
            {
                "id": "npc_goblin",
                "name": "Goblin",
                "role": "raider",
                "race": "goblin",
                "status": "active",
                "personality": "",
                "disposition": "hostile",
            },
        ],
    }


class TestCharacterSystemPrompt:
    """_pc_system.jinja 铁律验证——只关心 PC 自身/铁律，不含每 tick 变化的世界状态 / Only PC identity + iron rules, no per-tick world state."""

    def test_contains_iron_rules(self):
        rendered = _PROMPTS.get_template("decide/_pc_system.jinja").render(**_pc_context())
        assert "不要输出 JSON 以外的任何内容" in rendered
        assert "文本字段必须是中文" in rendered

    def test_self_identity_injected(self):
        """PC 自身身份（name/id）必须出现在 prompt 里 / PC self identity must appear in prompt."""
        rendered = _PROMPTS.get_template("decide/_pc_system.jinja").render(**_pc_context())
        assert "Hero" in rendered
        assert "pc_hero" in rendered

    def test_world_state_not_present(self):
        """场景/剧情/附近角色等每 tick 变化的内容不应出现在系统提示词里 / Per-tick world state must not leak into the system prompt."""
        rendered = _PROMPTS.get_template("decide/_pc_system.jinja").render(**_pc_context())
        assert "十字路口" not in rendered
        assert "Greta" not in rendered
        assert "注意十字路口的动静" not in rendered


# decide/pc_decide.jinja 携带每 tick 变化的世界状态 + 输出格式约束 / Per-tick world state + output format spec
class TestPCDecidePrompt:
    """decide/pc_decide.jinja 结构验证 / Structure validation."""

    def test_renders_with_full_context(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "十字路口" in rendered
        assert "Greta" in rendered

    def test_hints_injected(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "注意十字路口的动静" in rendered

    def test_scene_objects_injected(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "石碑" in rendered  # lineId is still in scene_objects list

    def test_nearby_pcs_and_actors_are_distinguished(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "附近的玩家角色（PC" in rendered
        assert "Alex" in rendered
        assert "附近的 NPC" in rendered
        assert "Greta" in rendered

    def test_hostile_actors_labeled_as_enemies(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "附近的敌人" in rendered
        assert "Goblin" in rendered

    def test_ids_exposed_for_target_reference(self):
        """附近人/物必须暴露 id，LLM 才能输出有效 target_id / Ids must be exposed so the LLM can output a valid target_id."""
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "obj_stele" in rendered
        assert "pc_alex" in rendered
        assert "npc_greta" in rendered
        assert "npc_goblin" in rendered

    def test_output_schema_has_required_fields(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert '"action_type"' in rendered
        assert '"target_id"' in rendered
        assert '"thought"' in rendered

    def test_mentions_combat_option(self):
        """combat 预留动作必须在字段说明中出现 / combat reserved action must appear in the field spec."""
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "combat" in rendered

    def test_requires_chinese_thought(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "中文" in rendered
