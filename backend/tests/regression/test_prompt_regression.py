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
        rendered = _PROMPTS.get_template("dm/_dm_system.jinja").render()
        assert len(rendered) > 0
        assert "DM" in rendered or "Dungeon Master" in rendered

    def test_contains_iron_rules(self):
        """包含三条核心铁律 / Contains 3 core iron rules."""
        rendered = _PROMPTS.get_template("dm/_dm_system.jinja").render()
        assert "不扮演任何角色" in rendered
        assert "不替任何角色做决策" in rendered
        assert "不写角色的对话内容" in rendered

    def test_requires_chinese_output(self):
        """要求中文输出 / Requires Chinese output."""
        rendered = _PROMPTS.get_template("dm/_dm_system.jinja").render()
        assert "简体中文" in rendered or "中文" in rendered

    def test_requires_json_only(self):
        """要求只输出 JSON / Requires JSON only output."""
        rendered = _PROMPTS.get_template("dm/_dm_system.jinja").render()
        assert "JSON" in rendered


class TestDMCreatePrompt:
    """dm_create.jinja 结构验证 / dm_create.jinja structure validation.

    dm_create 不再让 LLM 选择场景（场景由 world_init / party.decide_scene 确定性决定），
    只基于当前场景创造 plot_brief + hints。
    """

    def test_renders_with_empty_context(self):
        """空上下文不崩溃 / Renders with empty context."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            plot_brief_prev="",
            prev_narrative="",
        )
        assert len(rendered) > 0
        # 不应再要求 LLM 选场景 / no longer asks LLM to choose a scene
        assert "scene_id" not in rendered

    def test_renders_with_previous_plot(self):
        """有上一步剧情时注入 / Injects previous plot when present."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            plot_brief_prev="雾气弥漫的森林",
            prev_narrative="",
        )
        assert "雾气弥漫的森林" in rendered

    def test_output_schema_has_no_scene_id(self):
        """输出 schema 不再含 scene_id 字段（场景由确定性路径决定）."""
        rendered = _PROMPTS.get_template("dm/dm_create.jinja").render(
            plot_brief_prev="",
            prev_narrative="",
        )
        assert '"scene_id"' not in rendered


class TestDMNarratePrompt:
    """dm_narrate.jinja 结构验证 / dm_narrate.jinja structure validation."""

    def test_renders_with_empty_context(self):
        """空上下文不崩溃 / Renders with empty context."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="",
            hints=[],
            events=[],
        )
        assert len(rendered) > 0

    def test_injects_events(self):
        """注入事件 / Injects events."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="Story",
            hints=[],
            events=[{"type": "explore", "description": "alex found a clue"}],
        )
        assert "alex" in rendered

    def test_requires_sensory_detail(self):
        """要求感官细节 / Requires sensory detail."""
        rendered = _PROMPTS.get_template("dm/dm_narrate.jinja").render(
            plot_brief="",
            hints=[],
            events=[],
        )
        assert "感官" in rendered


class TestPartyTemplates:
    """party/ 下的集体讨论/决策模板回归 / Party (party/) template regression.

    验证 _party_system / party_discussion / party_decide 三个模板：
    1. 文件存在且能被加载（路径错误会抛 TemplateNotFound——曾因 party_service 路径
       多算一层 parent 导致 backend/prompts 而非 backend/src/prompts）
    2. 变量齐全时可正常渲染
    """

    def test_party_system_template_loads_and_renders(self):
        """_party_system.jinja 存在且可渲染 / _party_system.jinja loads and renders."""
        rendered = _PROMPTS.get_template("party/_party_system.jinja").render()
        assert len(rendered) > 0
        assert "讨论" in rendered

    def test_party_discussion_template_renders_with_vars(self):
        """_party_discussion.jinja 渲染需要 tick/current/pcs / Requires tick/current/pcs."""
        rendered = _PROMPTS.get_template("party/party_discussion.jinja").render(
            tick=3,
            current="village_elderwood",
            pcs="- Hero（id=pc-1）：长期目标=守护村庄",
        )
        assert "当前 tick：3" in rendered  # 变量被正确渲染
        assert "village_elderwood" in rendered
        assert "Hero" in rendered
        assert '"dialogue"' in rendered  # 要求 JSON dialogue 输出

    def test_party_decide_template_renders_with_vars(self):
        """_party_decide.jinja 渲染需要 tick/current/scenes/pcs."""
        rendered = _PROMPTS.get_template("party/party_decide.jinja").render(
            tick=3,
            current="village_elderwood",
            scenes="- village_elderwood：Elderwood Village\n- desert：Desert",
            pcs="- Hero（id=pc-1）：长期目标=守护村庄",
        )
        assert "village_elderwood" in rendered
        assert "desert" in rendered
        assert "Hero" in rendered
        assert "target_scene_id" in rendered  # 要求 JSON 决策输出
