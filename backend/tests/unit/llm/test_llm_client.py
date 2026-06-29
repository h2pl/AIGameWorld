"""LLM Schema 单元测试。per design/04-agent-layer.md §13 + 06-llm-dev-guide.md."""

from src.schemas.llm_output import BranchPoint, DMNarrativeSchema, DMOutput, SceneDirectionOutput


class TestLLMOutputSchemas:
    def test_dm_output_defaults(self):
        out = DMOutput(plot_brief="test")
        assert out.plot_brief == "test"
        assert out.instructions == []
        assert out.scene_direction.featured_pcs == []

    def test_dm_output_with_cast(self):
        out = DMOutput(
            plot_brief="The party enters the forest.",
            scene_direction=SceneDirectionOutput(
                featured_pcs=["alex", "maya"],
                featured_actors=["goblin_scout"],
                actor_motivations={"goblin_scout": "Ambush the party"},
                mood="tense",
            ),
        )
        assert len(out.scene_direction.featured_pcs) == 2
        assert out.scene_direction.mood == "tense"
        assert out.scene_direction.actor_motivations["goblin_scout"] == "Ambush the party"

    def test_dm_narrative_schema(self):
        n = DMNarrativeSchema(
            narrative="The party ventures forth into the dark forest.",
            branch_points=[
                BranchPoint(
                    decision_maker="alex", decision="Enter forest", consequence="Unknown danger"
                )
            ],
            hooks_resolved=["hook_001"],
        )
        assert n.narrative.startswith("The party")
        assert len(n.branch_points) == 1
        assert "hook_001" in n.hooks_resolved

    def test_dm_narrative_empty(self):
        n = DMNarrativeSchema(narrative="")
        assert n.branch_points == []
        assert n.hooks_resolved == []

    def test_dm_output_json_schema(self):
        schema = DMOutput.model_json_schema()
        assert "plot_brief" in schema["properties"]
        assert "scene_direction" in schema["properties"]
        assert "instructions" in schema["properties"]

    def test_scene_direction_mood_default(self):
        d = SceneDirectionOutput()
        assert d.mood == "neutral"

    def test_branch_point_defaults(self):
        bp = BranchPoint()
        assert bp.decision_maker == ""
        assert bp.decision == ""
        assert bp.consequence == ""


class TestFallbackOutputs:
    def test_fallback_dm_output_empty(self):
        """降级输出应该是最小情境。per §2.3."""
        fb = DMOutput(plot_brief="平静的一天，没有特别事件。")
        assert len(fb.instructions) == 0
        assert "平静" in fb.plot_brief

    def test_fallback_narrative_empty(self):
        """Fallback narrative should contain a valid string."""
        fb = DMNarrativeSchema(narrative="(DM fell silent...)")
        assert "DM" in fb.narrative
