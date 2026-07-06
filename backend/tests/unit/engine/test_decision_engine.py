"""Decision Engine 校验规则测试 / Decision engine validation rule tests."""

from src.engine.decision.decision_engine import _validate
from src.schemas.llm_output import CharacterActionSchema


class TestValidateActionTarget:
    """action_type 与 target 一致性校验 / action_type <-> target consistency."""

    def test_wait_forces_target_none(self):
        """wait 动作强制清空 target / wait forces target to be cleared."""
        result = _validate(
            CharacterActionSchema(
                action_type="wait",
                target_id="npc_greta",
                target_type="actor",
                thought="先看看情况。",
                reasoning="观望",
            )
        )
        assert result.action_type == "wait"
        assert result.target_id is None
        assert result.target_type is None

    def test_talk_without_target_falls_back_to_wait(self):
        """talk 但没有 target，降级为 wait / talk without a target falls back to wait."""
        result = _validate(
            CharacterActionSchema(action_type="talk", thought="想找人聊聊", reasoning="想说点什么")
        )
        assert result.action_type == "wait"
        assert result.target_id is None
        assert result.target_type is None

    def test_talk_with_mismatched_target_type_falls_back_to_wait(self):
        """talk 的 target_type 必须是 pc/actor，不能是 scene_object / talk requires pc/actor target_type."""
        result = _validate(
            CharacterActionSchema(
                action_type="talk",
                target_id="obj_stele",
                target_type="scene_object",
                thought="跟石碑说话似乎没用。",
                reasoning="跟石碑说话？",
            )
        )
        assert result.action_type == "wait"
        assert result.target_id is None
        assert result.target_type is None

    def test_talk_with_valid_target_kept(self):
        """talk 有合法 target 且在当前场景中时保留 / talk with valid target present in scene is kept."""
        from src.domain.actor import Actor

        result = _validate(
            CharacterActionSchema(
                action_type="talk",
                target_id="npc_greta",
                target_type="actor",
                thought="Greta 应该知道消息。",
                reasoning="打听消息",
            ),
            actors={"npc_greta": Actor(id="npc_greta", name="Greta")},
        )
        assert result.action_type == "talk"
        assert result.target_id == "npc_greta"
        assert result.target_type == "actor"

    def test_talk_with_target_not_in_scene_downgrades(self):
        """talk 目标不在当前场景中时降级为 wait / talk target not in scene → wait."""
        result = _validate(
            CharacterActionSchema(
                action_type="talk",
                target_id="npc_missing",
                target_type="actor",
                thought="人不在场。",
                reasoning="找人",
            ),
            actors={},
        )
        assert result.action_type == "wait"
        assert result.target_id is None

    def test_interact_requires_scene_object_target(self):
        """interact 的 target_type 必须是 scene_object / interact requires scene_object target_type."""
        result = _validate(
            CharacterActionSchema(
                action_type="interact",
                target_id="npc_greta",
                target_type="actor",
                thought="这不是物体。",
                reasoning="想互动",
            )
        )
        assert result.action_type == "wait"

    def test_combat_requires_pc_or_actor_target(self):
        """combat 的 target_type 必须是 pc/actor / combat requires pc/actor target_type."""
        result = _validate(
            CharacterActionSchema(
                action_type="combat",
                target_id="obj_stele",
                target_type="scene_object",
                thought="石碑不是敌人。",
                reasoning="攻击石碑？",
            )
        )
        assert result.action_type == "wait"

    def test_unknown_action_type_falls_back_to_wait(self):
        """未知 action_type 降级为 wait / Unknown action_type falls back to wait."""
        result = _validate(
            CharacterActionSchema(
                action_type="move",
                target_id="npc_greta",
                target_type="actor",
                thought="先走过去。",
                reasoning="走过去",
            )
        )
        assert result.action_type == "wait"
        assert result.target_id is None
        assert result.target_type is None

    def test_empty_reasoning_defaults_to_wait_message(self):
        """空 reasoning 使用默认文案 / Empty reasoning uses the default fallback text."""
        result = _validate(
            CharacterActionSchema(action_type="wait", thought="再等等。", reasoning="")
        )
        assert result.reasoning == "等待时机。"

    def test_empty_thought_gets_default(self):
        """空 thought 使用默认文案 / Empty thought uses the default fallback text."""
        result = _validate(CharacterActionSchema(action_type="wait", thought="", reasoning="观望"))
        assert result.thought == "我做出了这个决定。"
