"""Interact Engine 单元测试——移动/LLM 裁决/记忆 / Interact tests: move, LLM judge, memory."""

from unittest.mock import AsyncMock

import pytest

from src.domain.player_character import PlayerCharacter
from src.domain.scene_object import SceneObject, SceneObjectType
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


def _pc(position_x: int = 0, position_y: int = 0) -> PlayerCharacter:
    return PlayerCharacter(
        id="pc1",
        name="pc1",
        role="",
        personality="",
        position_x=position_x,
        position_y=position_y,
    )


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
        pc = _pc(position_x=0, position_y=0)
        event = await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene={"map_width": 40, "map_height": 40},
            scene_objects=[
                {
                    "id": "chest1",
                    "name": "宝箱",
                    "object_type": "container",
                    "position_x": 10,
                    "position_y": 10,
                    "interact_data": {"locked": False},
                },
            ],
            pcs={"pc1": pc},
            config=_config(scene_obj=chest, llm=llm),
        )
        assert event.kind == "pc_interact"
        assert len(event.waypoints) == 2
        final = event.waypoints[-1]
        assert abs(final["x"] - 10) <= 1 and abs(final["y"] - 10) <= 1
        assert pc.position_x == final["x"]
        assert pc.position_y == final["y"]

    @pytest.mark.asyncio
    async def test_interact_generates_success(self):
        """LLM 生成交互成功结果 / LLM generates successful interact result."""
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
            scene={"map_width": 40, "map_height": 40},
            scene_objects=[
                {
                    "id": "chest1",
                    "name": "宝箱",
                    "object_type": "container",
                    "position_x": 5,
                    "position_y": 5,
                    "interact_data": {"locked": False},
                },
            ],
            pcs={"pc1": _pc(position_x=0, position_y=0)},
            config=_config(scene_obj=chest, llm=llm),
        )
        assert event.success is True
        assert "他掀开沉重的箱盖" in event.narration

    @pytest.mark.asyncio
    async def test_interact_llm_returns_failure(self):
        """LLM 判定交互失败 / LLM judges interaction as failure."""
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
            scene={"map_width": 40, "map_height": 40},
            scene_objects=[
                {
                    "id": "trap1",
                    "name": "毒刺陷阱",
                    "object_type": "trap",
                    "position_x": 5,
                    "position_y": 5,
                    "interact_data": {"dc": 15},
                },
            ],
            pcs={"pc1": _pc(position_x=0, position_y=0)},
            config=_config(scene_obj=trap, llm=llm),
        )
        assert event.success is False
        assert "毒针" in event.narration

    @pytest.mark.asyncio
    async def test_interact_stores_memory(self):
        """交互结果写入 pc_memory_map / Interaction result is staged into state memory map."""
        chest = SceneObject(
            id="chest1",
            name="宝箱",
            object_type=SceneObjectType.CONTAINER,
            interact_data={"locked": False},
            position_x=5,
            position_y=5,
        )
        scene_repo = AsyncMock()
        scene_repo.load_all = AsyncMock(return_value={"chest1": chest})
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=InteractOutputSchema(success=True, narration="成功打开。")
        )
        config = {
            "configurable": {
                "repos": {"scene": scene_repo},
                "llm": llm,
            }
        }
        pc_memory_map: dict[str, list[dict]] = {}
        await process_interact_action(
            decision={"type": "interact", "pc_id": "pc1", "target_id": "chest1"},
            scene={"map_width": 40, "map_height": 40},
            scene_objects=[
                {
                    "id": "chest1",
                    "name": "宝箱",
                    "object_type": "container",
                    "position_x": 5,
                    "position_y": 5,
                    "interact_data": {"locked": False},
                },
            ],
            pcs={"pc1": _pc(position_x=0, position_y=0)},
            tick=3,
            pc_memory_map=pc_memory_map,
            config=config,
        )
        assert len(pc_memory_map.get("pc1", [])) == 1
        mem = pc_memory_map["pc1"][0]
        assert mem["pc_id"] == "pc1"  # 记忆归属 PC / Memory belongs to PC
        assert mem["tick"] == 3  # tick 号 / Tick number
        assert mem["memory_type"] == "interact"
