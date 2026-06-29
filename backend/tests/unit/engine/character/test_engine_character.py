"""Character Engine 单元测试 / Character Engine unit tests."""
from src.schemas.request import ActorDecideRequest, PCDecideRequest


class TestPCDecide:
    def test_known_pc_returns_action(self):
        """alex → explore action / alex 返回 explore 行动."""
        from src.engine.character.pc_decide import pc_decide

        result = pc_decide(PCDecideRequest(pc_id="alex", plot_brief="test", tick=0))
        assert result.character_id == "alex"
        assert result.type == "explore"
        assert len(result.description) > 0

    def test_unknown_pc_returns_idle(self):
        """未知 PC → idle fallback / Unknown PC returns idle."""
        from src.engine.character.pc_decide import pc_decide

        result = pc_decide(PCDecideRequest(pc_id="stranger", plot_brief="test", tick=0))
        assert result.character_id == "stranger"
        assert result.type == "idle"
        assert "waits" in result.description

    def test_different_pcs_return_different_actions(self):
        """不同 PC 返回不同 action 类型 / Different PCs return different action types."""
        from src.engine.character.pc_decide import pc_decide

        alex = pc_decide(PCDecideRequest(pc_id="alex", plot_brief="test", tick=0))
        maya = pc_decide(PCDecideRequest(pc_id="maya", plot_brief="test", tick=0))
        assert alex.type != maya.type


class TestActorDecide:
    def test_known_actor_returns_action(self):
        """innkeeper → social action / innkeeper 返回 social 行动."""
        from src.engine.character.actor_decide import actor_decide

        result = actor_decide(ActorDecideRequest(actor_id="innkeeper", plot_brief="test", tick=0))
        assert result.character_id == "innkeeper"
        assert result.type == "social"
        assert len(result.description) > 0

    def test_unknown_actor_returns_idle(self):
        """未知 Actor → idle fallback / Unknown actor returns idle."""
        from src.engine.character.actor_decide import actor_decide

        result = actor_decide(ActorDecideRequest(actor_id="nobody", plot_brief="test", tick=0))
        assert result.character_id == "nobody"
        assert result.type == "idle"

    def test_different_actors_return_different_actions(self):
        """不同 Actor 返回不同 action 类型 / Different actors return different action types."""
        from src.engine.character.actor_decide import actor_decide

        innkeeper = actor_decide(ActorDecideRequest(actor_id="innkeeper", plot_brief="test", tick=0))
        guard = actor_decide(ActorDecideRequest(actor_id="guard", plot_brief="test", tick=0))
        assert innkeeper.type != guard.type
