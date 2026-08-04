"""LLM Schema 单元测试 / LLM Schema unit tests.

验证 DMOutput（hints/plot_brief，不含 scene_id——场景由 world_init/party 确定性裁决）
和 DMNarrativeSchema（narrative）Pydantic 模型.
"""

from src.schemas.llm_output import DMNarrativeSchema, DMOutput


class TestLLMOutputSchemas:
    def test_dm_output_defaults(self):
        out = DMOutput(plot_brief="test")
        assert out.plot_brief == "test"
        assert out.hints == []

    def test_dm_output_with_hints(self):
        out = DMOutput(
            plot_brief="The party enters the forest.",
            hints=["环境提示"],
        )
        assert len(out.hints) == 1

    def test_dm_narrative_schema(self):
        n = DMNarrativeSchema(narrative="The party ventures forth into the dark forest.")
        assert n.narrative.startswith("The party")

    def test_dm_narrative_empty(self):
        n = DMNarrativeSchema(narrative="")
        assert n.narrative == ""

    def test_dm_output_json_schema(self):
        schema = DMOutput.model_json_schema()
        assert "plot_brief" in schema["properties"]
        assert "scene_id" not in schema["properties"]
        assert "hints" in schema["properties"]


class TestFallbackOutputs:
    def test_fallback_dm_output_empty(self):
        fb = DMOutput(plot_brief="平静的一天，没有特别事件。")
        assert len(fb.hints) == 0
        assert "平静" in fb.plot_brief

    def test_fallback_narrative_empty(self):
        fb = DMNarrativeSchema(narrative="(DM fell silent...)")
        assert "DM" in fb.narrative
