"""Interact Engine 单元测试——移动/LLM 裁决/记忆 / Interact tests: move, LLM judge, memory."""

from unittest.mock import AsyncMock

import pytest

from src.engine.interact.interact_engine import process_interact_action
from src.schemas.llm_output import InteractOutputSchema


# mock repo config helper / mock repo 构造辅助函数
def _config(scene_obj=None, llm=None):
    """构造带 repo mock 的 config / Build config with repo mocks."""
    scene_repo = AsyncMock()
    scene_repo.load_all = AsyncMock(return_value={scene_obj.id: scene_obj} if scene_obj else {})
    memory_repo = AsyncMock()
    memory_repo.retrieve = AsyncMock(return_value=[])
    memory_repo.store = AsyncMock(return_value=None)
    cfg = {"configurable": {"repos": {"scene": scene_repo, "memory": memory_repo}}}
    if llm:
        cfg["configurable"]["llm"] = llm
    return cfg


class TestInteractEngine:
    """interact engine 单元测试 / Interact engine unit tests."""

    @pytest.mark.asyncio
    async def test_non_interact_action_skipped(self):
        """非 interact 类型被跳过 / Non-interact action is skipped."""
        event = await process_interact_action(decision={"type": "talk", "pc_id": "pc1"})
        assert event is None

    @pytest.mark.asyncio
    async def test_interact_without_target_skipped(self):
        """无目标物体时跳过 / Interact without target is skipped."""
        event = await process_interact_action(decision={"type": "interact", "pc_id": "pc1"})
        assert event is None

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
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractOutputSchema(success=True, narration="打开了宝箱。")
        )
        pc_state_map = {
            "pc1": {"name": "pc1", "role": "", "personality": "", "position_x": 0, "position_y": 0},
        }
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
                },
            ],
        }
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene_info=scene_info,
            pc_state_map=pc_state_map,
            config=_config(scene_obj=chest, llm=llm),
        )
        assert event.kind == "pc_interact"
        assert len(event.waypoints) == 2
        final = event.waypoints[-1]
        assert abs(final["x"] - 10) <= 1 and abs(final["y"] - 10) <= 1
        assert pc_state_map["pc1"]["position_x"] == final["x"]
        assert pc_state_map["pc1"]["position_y"] == final["y"]

    @pytest.mark.asyncio
    async def test_interact_generates_success(self):
        """LLM 生成交互成功结果 / LLM generates successful interact result."""
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
            return_value=InteractOutputSchema(
                success=True, narration="他掀开沉重的箱盖，发现里面空无一物。"
            )
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
                    },
                ],
            },
            pc_state_map={
                "pc1": {
                    "name": "pc1",
                    "role": "",
                    "personality": "",
                    "position_x": 0,
                    "position_y": 0,
                }
            },
            config=_config(scene_obj=chest, llm=llm),
        )
        assert event.success is True
        assert "他掀开沉重的箱盖" in event.narration

    @pytest.mark.asyncio
    async def test_interact_llm_returns_failure(self):
        """LLM 判定交互失败 / LLM judges interaction as failure."""
        from src.domain.scene_object import SceneObject, SceneObjectType

        trap = SceneObject(
            id="trap1",
            name="毒刺陷阱",
            object_type=SceneObjectType.TRAP,
            interact_data={"dc": 15},
            position_x=5,
            position_y=5,
        )
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractOutputSchema(
                success=False,
                narration="他试图拆除陷阱，却被毒针刺中手指，一阵剧痛袭来。",
            )
        )
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "trap1"},
            scene_info={
                "scene": {"map_width": 40, "map_height": 40},
                "scene_objects": [
                    {
                        "id": "trap1",
                        "name": "毒刺陷阱",
                        "object_type": "trap",
                        "position_x": 5,
                        "position_y": 5,
                        "interact_data": {"dc": 15},
                    },
                ],
            },
            pc_state_map={
                "pc1": {
                    "name": "pc1",
                    "role": "",
                    "personality": "",
                    "position_x": 0,
                    "position_y": 0,
                }
            },
            config=_config(scene_obj=trap, llm=llm),
        )
        assert event.success is False
        assert "毒刺" in event.narration

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
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractOutputSchema(success=True, narration="成功打开。")
        )
        config = {
            "configurable": {
                "repos": {"scene": scene_repo, "memory": memory_repo},
                "llm": llm,
            }
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
                    },
                ],
            },
            pc_state_map={
                "pc1": {
                    "name": "pc1",
                    "role": "",
                    "personality": "",
                    "position_x": 0,
                    "position_y": 0,
                }
            },
            tick=3,
            config=config,
        )
        assert memory_repo.store.called
        call = memory_repo.store.call_args
        assert call.args[0] == "pc1"  # 记忆归属 PC / Memory belongs to PC
        assert call.args[2] == 3  # tick 号 / Tick number
