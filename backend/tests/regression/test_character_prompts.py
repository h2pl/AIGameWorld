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
        "plot_brief": "雾气在十字路口聚拢。",
        "hints": ["注意十字路口的动静"],
        "scene": {
            "id": "crossroad",
            "name": "十字路口",
            "type": "outdoor",
            "description": "雾气弥漫的十字路口。",
            "landmarks": ["石碑"],
            "exits": ["北：小镇", "南：森林"],
        },
        "scene_objects": [{"name": "石碑", "object_type": "landmark", "interactable": True}],
        "nearby_pcs": [{"name": "Alex", "role": "fighter", "race": "human", "status": "active"}],
        "nearby_actors": [
            {
                "name": "Greta",
                "role": "innkeeper",
                "race": "human",
                "status": "active",
                "personality": "Warm but sharp-eyed.",
                "disposition": "neutral",
            },
            {
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
    """_pc_system.jinja 铁律验证 / Iron rules validation."""

    def test_renders_for_pc(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "十字路口" in rendered
        assert "Greta" in rendered

    def test_contains_iron_rules(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "不要输出 JSON 以外的任何内容" in rendered
        assert "文本字段必须是中文" in rendered

    def test_hints_injected(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "注意十字路口的动静" in rendered

    def test_scene_objects_injected(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "石碑" in rendered

    def test_nearby_pcs_and_actors_are_distinguished(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "附近的玩家角色（PC）" in rendered
        assert "Alex" in rendered
        assert "附近的 NPC" in rendered
        assert "Greta" in rendered

    def test_hostile_actors_labeled_as_enemies(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "附近的敌人" in rendered
        assert "Goblin" in rendered

    def test_scene_exits_injected(self):
        rendered = _PROMPTS.get_template("_pc_system.jinja").render(**_pc_context())
        assert "北：小镇" in rendered


# decide/pc_decide.jinja 包含 _pc_system.jinja 并追加输出格式约束 / Includes _pc_system.jinja plus output format spec
class TestPCDecidePrompt:
    """decide/pc_decide.jinja 结构验证 / Structure validation."""

    def test_renders_with_full_context(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "十字路口" in rendered
        assert "Greta" in rendered

    def test_output_schema_has_required_fields(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert '"action_type"' in rendered
        assert '"target"' in rendered
        assert '"reasoning"' in rendered

    def test_requires_chinese_reasoning(self):
        rendered = _PROMPTS.get_template("decide/pc_decide.jinja").render(**_pc_context())
        assert "中文" in rendered
