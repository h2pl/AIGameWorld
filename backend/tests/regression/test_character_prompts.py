"""角色 Prompt 回归测试 / Character Prompt regression tests.

验证 PC/Actor 的 System Prompt 和 Jinja 模板在变更后仍满足安全铁律和结构要求。
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "src" / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


def _pc_context():
    return {
        "name": "Alex", "character_type": "pc", "role": "fighter",
        "character_arc": {"stage": "growth", "description": "Prove his worth"},
        "values": ["honor", "justice"], "long_term_goal": "Find his lost sister",
        "plot_brief": "雾气在十字路口聚拢。",
        "equipment": {"weapon_id": "longsword", "armor_id": "chain_mail"},
        "memories": [{"content": "昨天在酒馆遇到了一个可疑旅人。"}],
        "visible_characters": [{"name": "Greta", "role": "innkeeper", "attitude": "friendly"}],
    }


def _actor_context():
    return {
        "name": "Greta", "character_type": "actor", "role": "innkeeper",
        "personality": "Warm but sharp-eyed.", "functions": ["dialogue", "merchant"],
        "dm_motivation": "想打听失踪商队的消息",
        "plot_brief": "酒馆里来了几个冒险者。",
        "equipment": {}, "memories": [],
    }


class TestCharacterSystemPrompt:
    """_character_system.jinja 铁律验证 / Iron rules validation."""

    def test_renders_for_pc(self):
        rendered = _PROMPTS.get_template("_character_system.jinja").render(**_pc_context())
        assert "Alex" in rendered
        assert "价值观" in rendered

    def test_renders_for_actor(self):
        rendered = _PROMPTS.get_template("_character_system.jinja").render(**_actor_context())
        assert "Greta" in rendered
        assert "innkeeper" in rendered

    def test_contains_iron_rules(self):
        rendered = _PROMPTS.get_template("_character_system.jinja").render(**_pc_context())
        assert "不要输出 JSON 以外的任何内容" in rendered
        assert "文本字段必须是中文" in rendered

    def test_pc_arc_injected(self):
        rendered = _PROMPTS.get_template("_character_system.jinja").render(**_pc_context())
        assert "growth" in rendered
        assert "honor" in rendered

    def test_actor_motivation_injected(self):
        rendered = _PROMPTS.get_template("_character_system.jinja").render(**_actor_context())
        assert "打听失踪商队" in rendered


class TestPCDecidePrompt:
    """pc_decide.jinja 结构验证 / Structure validation."""

    def test_renders_with_full_context(self):
        rendered = _PROMPTS.get_template("character/pc_decide.jinja").render(**_pc_context())
        assert "Alex" in rendered
        assert "Greta" in rendered

    def test_output_schema_has_required_fields(self):
        rendered = _PROMPTS.get_template("character/pc_decide.jinja").render(**_pc_context())
        assert '"action_type"' in rendered
        assert '"target"' in rendered
        assert '"reasoning"' in rendered

    def test_requires_chinese_reasoning(self):
        rendered = _PROMPTS.get_template("character/pc_decide.jinja").render(**_pc_context())
        assert "中文" in rendered


class TestActorDecidePrompt:
    """actor_decide.jinja 结构验证 / Structure validation."""

    def test_renders_with_full_context(self):
        rendered = _PROMPTS.get_template("character/actor_decide.jinja").render(**_actor_context())
        assert "Greta" in rendered
        assert "innkeeper" in rendered

    def test_output_schema_has_required_fields(self):
        rendered = _PROMPTS.get_template("character/actor_decide.jinja").render(**_actor_context())
        assert '"action_type"' in rendered
        assert '"target"' in rendered
        assert '"reasoning"' in rendered
