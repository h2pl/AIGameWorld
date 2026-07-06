"""Interact Engine 单元测试 / Unit tests for interact engine."""

from unittest.mock import AsyncMock

import pytest

from src.engine.interact.interact_engine import process_interact_action
from src.schemas.llm_output import InteractNarrationSchema


def _config(scene_obj=None, pc=None, llm=None):
    """构造带 repo mock 的 config / Build config with repo mocks."""
    scene_repo = AsyncMock()
    scene_repo.load_all = AsyncMock(return_value={scene_obj.id: scene_obj} if scene_obj else {})
    pc_repo = AsyncMock()
    pc_repo.load_one = AsyncMock(return_value=pc)
    memory_repo = AsyncMock()
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo.store = AsyncMock(return_value=None)
    repos = {"scene": scene_repo, "char": pc_repo, "memory": memory_repo}
    cfg = {"configurable": {"repos": repos}}
    if llm:
        cfg["configurable"]["llm"] = llm
    return cfg


class TestInteractEngine:
    @pytest.mark.asyncio
    async def test_non_interact_action_skipped(self):
        """非 interact 类型被跳过 / Non-interact action is skipped."""
        event = await process_interact_action(
            decision={"type": "talk", "pc_id": "pc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_interact_without_target_skipped(self):
        """无目标物体时跳过 / Interact without target is skipped."""
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1"},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_interact_without_scene_object_auto_succeeds(self):
        """找不到目标物体时降级为无需检定直接成功 / No matching scene object falls back to auto-success."""
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
        )
        assert event["kind"] == "pc_interact"
        assert event["object_id"] == "chest1"
        assert event["success"] is True
        assert event["narration"]

    @pytest.mark.asyncio
    async def test_interact_moves_pc_to_adjacent(self):
        """PC 移动到物体旁边并记录 waypoints / PC moves adjacent and records waypoints."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
            position_x=10,
            position_y=10,
        )
        pc_state_map = {"pc1": {"position_x": 0, "position_y": 0}}
        scene_info = {
            "scene": {"map_width": 40, "map_height": 40},
            "scene_objects": [
                {
                    "id": "chest1",
                    "name": "宝箱",
                    "object_type": "container",
                    "position_x": 10,
                    "position_y": 10,
                    "interact_data": {"locked": False},
                }
            ],
            "pcs": [{"id": "pc1", "name": "pc1"}],
        }
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene_info=scene_info,
            pc_state_map=pc_state_map,
            config=_config(scene_obj=chest),
        )
        assert event["kind"] == "pc_interact"
        assert len(event["waypoints"]) == 2
        final = event["waypoints"][-1]
        # 最终位置在 (10,10) 旁边 / Final position is adjacent to chest
        assert abs(final["x"] - 10) <= 1 and abs(final["y"] - 10) <= 1
        assert pc_state_map["pc1"]["position_x"] == final["x"]
        assert pc_state_map["pc1"]["position_y"] == final["y"]

    @pytest.mark.asyncio
    async def test_interact_generates_narration_via_llm(self):
        """LLM 生成交互旁白 / LLM generates interaction narration."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
            position_x=5,
            position_y=5,
        )
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractNarrationSchema(narration="他掀开沉重的箱盖，发现里面空无一物。")
        )
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene_info={
                "scene": {"map_width": 40, "map_height": 40},
                "scene_objects": [
                    {
                        "id": "chest1",
                        "name": "宝箱",
                        "object_type": "container",
                        "position_x": 5,
                        "position_y": 5,
                        "interact_data": {"locked": False},
                    }
                ],
                "pcs": [{"id": "pc1", "name": "pc1"}],
            },
            pc_state_map={"pc1": {"position_x": 0, "position_y": 0}},
            config=_config(scene_obj=chest, llm=llm),
        )
        assert "他掀开沉重的箱盖" in event["narration"]

    @pytest.mark.asyncio
    async def test_interact_stores_memory(self):
        """交互结果存入记忆 / Interaction result is stored as memory."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
            position_x=5,
            position_y=5,
        )
        memory_repo = AsyncMock()
        memory_repo.retrieve = AsyncMock(return_value=[])
        memory_repo.store = AsyncMock(return_value=None)
        scene_repo = AsyncMock()
        scene_repo.load_all = AsyncMock(return_value={"chest1": chest})
        pc_repo = AsyncMock()
        pc_repo.load_one = AsyncMock(return_value=None)
        config = {
            "configurable": {"repos": {"scene": scene_repo, "char": pc_repo, "memory": memory_repo}}
        }
        await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene_info={
                "scene": {"map_width": 40, "map_height": 40},
                "scene_objects": [
                    {
                        "id": "chest1",
                        "name": "宝箱",
                        "object_type": "container",
                        "position_x": 5,
                        "position_y": 5,
                        "interact_data": {"locked": False},
                    }
                ],
                "pcs": [{"id": "pc1", "name": "pc1"}],
            },
            pc_state_map={"pc1": {"position_x": 0, "position_y": 0}},
            tick=3,
            config=config,
        )
        assert memory_repo.store.called
        call = memory_repo.store.call_args
        assert call.args[0] == "pc1"
        assert call.args[2] == 3
