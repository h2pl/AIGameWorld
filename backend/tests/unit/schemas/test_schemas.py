"""Schema 验证测试—— request / response / llm_output 全部 DTO."""

import pytest
from pydantic import ValidationError

from src.schemas.llm_output import (
    DMNarrativeSchema,
    DMOutput,
)
from src.schemas.request import (
    CharacterLoadRequest,
    CombatRequest,
    DialogueRequest,
    DMCreateRequest,
    DMNarrateRequest,
    ItemQueryRequest,
    PCDecideRequest,
    QuestRequest,
    ReflectionRequest,
    SceneObjectInteractRequest,
    SceneProcessRequest,
    StoryAdvanceRequest,
    SummarizerRequest,
)
from src.schemas.response import (
    CharacterResponse,
    CombatResponse,
    DialogueResponse,
    DMCreateResponse,
    DMNarrateResponse,
    ItemResponse,
    PCDecideResponse,
    QuestResponse,
    ReflectionResponse,
    SceneProcessResponse,
    SummarizerResponse,
)


# ============================================================
# Request DTO
# ============================================================
class TestRequestSchemas:
    def test_dm_create_request_defaults(self):
        r = DMCreateRequest()
        assert r.tick == 0
        assert r.plot_brief == ""

    def test_dm_narrate_request_with_hints(self):
        r = DMNarrateRequest(hints=["探索酒馆", "与NPC交谈"])
        assert len(r.hints) == 2
        assert r.hints[0] == "探索酒馆"

    def test_scene_process_request(self):
        r = SceneProcessRequest(tick=5, scene_id="tavern")
        assert r.tick == 5
        assert r.scene_id == "tavern"

    def test_pc_decide_request(self):
        r = PCDecideRequest(pc_id="hero_1", plot_brief="遭遇怪物", tick=3)
        assert r.pc_id == "hero_1"
        assert r.tick == 3

    def test_combat_request(self):
        from src.schemas.request import CombatParticipant

        r = CombatRequest(
            participants=[
                CombatParticipant(name="a", team="party"),
                CombatParticipant(name="b", team="enemy"),
            ],
            round=2,
        )
        assert len(r.participants) == 2

    def test_dialogue_request(self):
        r = DialogueRequest(speaker="pc1", target="npc1", intent="persuade")
        assert r.intent == "persuade"

    def test_quest_request(self):
        r = QuestRequest(quests=[{"id": "q1"}])
        assert len(r.quests) == 1

    def test_reflection_request(self):
        r = ReflectionRequest(character_id="pc1", memories=[{"text": "met dragon"}])
        assert len(r.memories) == 1

    def test_summarizer_request(self):
        r = SummarizerRequest(tick=10)
        assert r.tick == 10

    def test_story_advance_request(self):
        r = StoryAdvanceRequest(tick=1, narrative="party reached town")
        assert r.narrative == "party reached town"

    def test_item_query_request(self):
        r = ItemQueryRequest(item_id="sword_01")
        assert r.item_id == "sword_01"

    def test_scene_object_interact_request(self):
        r = SceneObjectInteractRequest(object_id="door_1", character_id="pc1", action_type="open")
        assert r.object_id == "door_1"

    def test_character_load_request(self):
        r = CharacterLoadRequest(character_id="hero_1")
        assert r.character_id == "hero_1"


# ============================================================
# Response DTO
# ============================================================
class TestResponseSchemas:
    def test_dm_create_response(self):
        r = DMCreateResponse(hints=["探索"], plot_brief="故事", scene_id="tavern")
        assert r.hints == ["探索"]
        assert r.scene_id == "tavern"

    def test_dm_narrate_response(self):
        r = DMNarrateResponse(narrative_out="伟大的冒险开始了。")
        assert "冒险" in r.narrative_out

    def test_scene_process_response(self):
        r = SceneProcessResponse(tick_events_out=[{"type": "dm_instruction"}])
        assert len(r.tick_events_out) == 1

    def test_pc_decide_response(self):
        r = PCDecideResponse(pc_id="pc1", type="attack", description="strikes")
        assert r.pc_id == "pc1"

    def test_combat_response(self):
        r = CombatResponse(winner="pc1", combat_log=[{"round": 1}])
        assert r.winner == "pc1"

    def test_dialogue_response(self):
        r = DialogueResponse(success=True, content="hello")
        assert r.success is True

    def test_quest_response(self):
        r = QuestResponse(completed_ids=["q1", "q2"])
        assert len(r.completed_ids) == 2

    def test_reflection_response(self):
        r = ReflectionResponse(insights_out=[{"key": "val"}])
        assert len(r.insights_out) == 1

    def test_summarizer_response(self):
        r = SummarizerResponse(compressed=True, summary_text="sum")
        assert r.compressed

    def test_character_response_defaults(self):
        r = CharacterResponse()
        assert r.character_type == "pc"
        assert r.alive is True
        assert r.hp == 10

    def test_item_response_defaults(self):
        r = ItemResponse(id="sword_01", name="Sword")
        assert r.rarity == "common"

    def test_scene_process_response_with_combat(self):
        r = SceneProcessResponse(tick_events_out=[{"type": "combat"}, {"type": "dialogue"}])
        assert len(r.tick_events_out) == 2


# ============================================================
# LLM Output Schema
# ============================================================
class TestLLMOutputSchemas:
    def test_dm_output_validates_hints(self):
        o = DMOutput(hints=["探索酒馆", "与NPC交谈"], plot_brief="故事")
        assert len(o.hints) == 2
        assert isinstance(o.hints[0], str)

    def test_dm_output_json_roundtrip(self):
        o = DMOutput(
            plot_brief="测试",
            hints=["action1"],
            scene_id="tavern",
        )
        dumped = o.model_dump_json()
        loaded = DMOutput.model_validate_json(dumped)
        assert loaded.plot_brief == "测试"
        assert loaded.scene_id == "tavern"

    def test_dm_narrative_schema(self):
        n = DMNarrativeSchema(narrative="冒险开始了。")
        assert n.narrative == "冒险开始了。"

    def test_dm_narrative_schema_json_roundtrip(self):
        n = DMNarrativeSchema(narrative="test")
        loaded = DMNarrativeSchema.model_validate_json(n.model_dump_json())
        assert loaded.narrative == "test"

    def test_dm_output_defaults(self):
        o = DMOutput(plot_brief="test")
        assert o.scene_id == ""
        assert o.hints == []

    def test_dm_output_rejects_dict_hints(self):
        """hints 必须是 list[str]，传入 dict 应报错."""
        with pytest.raises(ValidationError):
            DMOutput(plot_brief="test", hints=[{"type": "wrong"}])
