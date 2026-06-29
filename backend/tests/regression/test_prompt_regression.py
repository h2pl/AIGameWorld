"""Prompt 回归测试 / Prompt regression tests.

验证 DM / Character 的 System Prompt 和 Jinja 模板在变更后仍满足安全铁律和结构要求。
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "src" / "prompts"
_PROMPTS = Environment(loader=FileSystemLoader(_PROMPTS_ROOT))


class TestDMSystemPrompt:
    """DM system prompt 铁律验证 / DM system prompt iron rules."""

    def test_system_prompt_loaded(self):
        """_dm_system.jinja 存在且可渲染 / _dm_system.jinja exists and renders."""
        rendered = _PROMPTS.get_template("_dm_system.jinja").render()
        assert len(rendered) > 0
        assert "DM" in rendered or "Dungeon Master" in rendered

    def test_contains_iron_rules(self):
        """包含三条核心铁律 / Contains 3 core iron rules."""
        rendered = _PROMPTS.get_template("_dm_system.jinja").render()
        assert "不扮演任何角色" in rendered
        assert "不替任何角色做决策" in rendered
        assert "不写角色的对话内容" in rendered

    def test_requires_chinese_output(self):
        """要求中文输出 / Requires Chinese output."""
        rendered = _PROMPTS.get_template("_dm_system.jinja").render()
        assert "简体中文" in rendered or "中文" in rendered

    def test_requires_json_only(self):
        """要求只输出 JSON / Requires JSON only output."""
        rendered = _PROMPTS.get_template("_dm_system.jinja").render()
        assert "JSON" in rendered


class TestDMCreatePrompt:
    """dm_create.jinja 结构验证 / dm_create.jinja structure validation."""

    def test_renders_with_empty_context(self):
        """空上下文不崩溃 / Renders with empty context."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=[],
            active_hooks=[],
            recent_summary="",
            plot_brief_prev="",
            pacing={},
        )
        assert len(rendered) > 0

    def test_renders_with_story_arcs(self):
        """有剧情线时注入 / Injects story arcs when present."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=[{"title": "Test", "stage": "铺陈"}],
            active_hooks=[],
            recent_summary="",
            plot_brief_prev="plot",
            pacing={},
        )
        assert "Test" in rendered

    def test_output_schema_contains_mood(self):
        """输出 schema 含 mood 字段 / Output schema includes mood field."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            story_arcs=[],
            active_hooks=[],
            recent_summary="",
            plot_brief_prev="",
            pacing={},
        )
        assert '"mood"' in rendered


class TestDMNarratePrompt:
    """dm_narrate.jinja 结构验证 / dm_narrate.jinja structure validation."""

    def test_renders_with_empty_context(self):
        """空上下文不崩溃 / Renders with empty context."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="",
            character_actions=[],
            events=[],
            combat_result=None,
            cast_changes=[],
        )
        assert len(rendered) > 0

    def test_injects_character_actions(self):
        """注入角色行动 / Injects character actions."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="Story",
            character_actions=[
                {"character_id": "alex", "type": "explore", "description": "scanning"}
            ],
            events=[],
            combat_result=None,
            cast_changes=[],
        )
        assert "alex" in rendered

    def test_requires_sensory_detail(self):
        """要求感官细节 / Requires sensory detail."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="",
            character_actions=[],
            events=[],
            combat_result=None,
            cast_changes=[],
        )
        assert "感官" in rendered
