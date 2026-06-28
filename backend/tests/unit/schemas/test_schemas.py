"""Schema 验证测试—— request / response / llm_output 全部 DTO."""
import pytest
from pydantic import ValidationError

from src.schemas.request import (
    DMCreateRequest, DMNarrateRequest, WorldUpdateRequest,
    PCDecideRequest, ActorDecideRequest,
    CombatRequest, DialogueRequest, ExplorationRequest, QuestRequest,
    ReflectionRequest, SummarizerRequest,
    StoryAdvanceRequest, ItemQueryRequest, SceneObjectInteractRequest,
    CharacterLoadRequest,
)
from src.schemas.response import (
    QuestResponse, ReflectionResponse, SummarizerResponse,
    DMCreateResponse, DMNarrateResponse, WorldUpdateResponse,
    PCDecideResponse, ActorDecideResponse,
    CombatResponse, DialogueResponse, ExplorationResponse,
    StoryAdvanceResponse, ItemResponse, SceneObjectInteractResponse,
    CharacterResponse,
)
from src.schemas.llm_output import (
    SceneDirectionOutput, BranchPoint, DMOutput, DMNarrativeSchema,
)
from src.domain.instruction import DMInstruction, SceneDirection
from src.domain.action import Action
from src.domain.event import Event


# ============================================================
# Request DTO
# ============================================================
class TestRequestSchemas:
    def test_dm_create_request_defaults(self):
        r = DMCreateRequest()
        assert r.tick == 0
        assert r.plot_brief == ""

    def test_dm_narrate_request_with_instructions(self):
        r = DMNarrateRequest(dm_instructions=["探索酒馆", "与NPC交谈"])
        assert len(r.dm_instructions) == 2
        assert r.dm_instructions[0] == "探索酒馆"

    def test_world_update_request(self):
        r = WorldUpdateRequest(tick=5, dm_instructions=["测试"])
        assert r.tick == 5
        assert r.dm_instructions == ["测试"]

    def test_pc_decide_request(self):
        r = PCDecideRequest(pc_id="hero_1", plot_brief="遭遇怪物", tick=3)
        assert r.pc_id == "hero_1"
        assert r.tick == 3

    def test_actor_decide_request(self):
        r = ActorDecideRequest(actor_id="npc_guard")
        assert r.actor_id == "npc_guard"

    def test_combat_request(self):
        r = CombatRequest(participants=["a", "b"], round=2)
        assert len(r.participants) == 2

    def test_dialogue_request(self):
        r = DialogueRequest(speaker="pc1", target="npc1", intent="persuade")
        assert r.intent == "persuade"

    def test_exploration_request(self):
        r = ExplorationRequest(character_id="pc1", action_type="search")
        assert r.action_type == "search"

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
        r = DMCreateResponse(instructions_out=["探索"], plot_brief="故事", scene_direction={"mood": "dark"})
        assert r.instructions_out == ["探索"]
        assert r.scene_direction["mood"] == "dark"

    def test_dm_narrate_response(self):
        r = DMNarrateResponse(narrative_out="伟大的冒险开始了。")
        assert "冒险" in r.narrative_out

    def test_world_update_response(self):
        r = WorldUpdateResponse(events_out=[{"type": "dm_instruction"}])
        assert len(r.events_out) == 1

    def test_pc_decide_response(self):
        r = PCDecideResponse(character_id="pc1", type="attack", description="strikes")
        assert r.character_id == "pc1"

    def test_actor_decide_response(self):
        r = ActorDecideResponse(character_id="npc1", type="flee")
        assert r.character_id == "npc1"

    def test_combat_response(self):
        r = CombatResponse(winner="pc1", combat_log=[{"round": 1}])
        assert r.winner == "pc1"

    def test_dialogue_response(self):
        r = DialogueResponse(success=True, content="hello")
        assert r.success is True

    def test_exploration_response(self):
        r = ExplorationResponse(success=True, result={"found": "gold"})
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

    def test_dm_create_response_from_entity(self):
        """from_entity 将 DMInstruction.model_dump() dict 序列化为字符串."""
        inst = SceneDirection(type="scene_direction", featured_pcs=["pc1"], description="dir")
        r = DMCreateResponse.from_entity(inst)
        assert len(r.instructions_out) == 1
        assert isinstance(r.instructions_out[0], str)

    def test_pc_decide_response_from_entity(self):
        action = Action(character_id="pc1", action_type="attack", reasoning="enemy near")
        r = PCDecideResponse.from_entity(action)
        assert r.type == "attack"

    def test_world_update_response_from_entities(self):
        events = [Event(id="e1", tick=0, type="combat"), Event(id="e2", tick=0, type="dialogue")]
        r = WorldUpdateResponse.from_entities(events)
        assert len(r.events_out) == 2


# ============================================================
# LLM Output Schema
# ============================================================
class TestLLMOutputSchemas:
    def test_dm_output_validates_str_instructions(self):
        o = DMOutput(instructions=["探索酒馆", "与NPC交谈"], plot_brief="故事")
        assert len(o.instructions) == 2
        assert isinstance(o.instructions[0], str)

    def test_dm_output_json_roundtrip(self):
        import json
        o = DMOutput(plot_brief="测试", instructions=["action1"],
                      scene_direction=SceneDirectionOutput(featured_pcs=["pc1"], mood="tense"))
        dumped = o.model_dump_json()
        loaded = DMOutput.model_validate_json(dumped)
        assert loaded.plot_brief == "测试"
        assert loaded.scene_direction.mood == "tense"

    def test_dm_narrative_schema(self):
        n = DMNarrativeSchema(narrative="冒险开始了。", branch_points=[],
                               hooks_resolved=["hook1"])
        assert n.narrative == "冒险开始了。"
        assert len(n.hooks_resolved) == 1

    def test_dm_narrative_schema_json_roundtrip(self):
        n = DMNarrativeSchema(narrative="test")
        loaded = DMNarrativeSchema.model_validate_json(n.model_dump_json())
        assert loaded.narrative == "test"

    def test_branch_point(self):
        bp = BranchPoint(decision_maker="pc1", decision="attack", consequence="victory")
        assert bp.decision_maker == "pc1"

    def test_scene_direction_output_defaults(self):
        sd = SceneDirectionOutput()
        assert sd.mood == "neutral"
        assert sd.featured_pcs == []

    def test_dm_output_rejects_dict_instructions(self):
        """instructions 必须是 list[str]，传入 dict 应报错."""
        with pytest.raises(ValidationError):
            DMOutput(plot_brief="test", instructions=[{"type": "wrong"}])
