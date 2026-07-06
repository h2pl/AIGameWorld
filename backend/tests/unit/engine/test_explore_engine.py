"""Explore Engine 单元测试 / Unit tests for explore engine."""

from unittest.mock import AsyncMock

import pytest

from src.engine.explore.explore_engine import process_explore_action
from src.schemas.llm_output import ExploreOutputSchema, ExploreWaypointSchema


class TestExploreEngine:
    @pytest.mark.asyncio
    async def test_non_explore_action_skipped(self):
        """非 explore 类型被跳过 / Non-explore action is skipped."""
        event = await process_explore_action(
            decision={"type": "talk", "pc_id": "pc1"},
            scene_info={},
            pc_state_map={},
        )
        assert event is None

    @pytest.mark.asyncio
    async def test_without_llm_falls_back_to_random_waypoints_with_narrations(self):
        """无 LLM 时生成随机路径和简单旁白 / Without LLM, random waypoints + narrations."""
        pc_state_map = {"pc1": {"position_x": 5, "position_y": 5}}
        scene_info = {
            "scene": {"map_width": 40, "map_height": 40},
            "pcs": [{"id": "pc1", "name": "pc1"}],
        }
        event = await process_explore_action(
            decision={"type": "explore", "pc_id": "pc1"},
            scene_info=scene_info,
            pc_state_map=pc_state_map,
        )
        assert event["kind"] == "pc_explore"
        assert event["pc_id"] == "pc1"
        assert len(event["waypoints"]) >= 2
        assert all("narration" in wp for wp in event["waypoints"])
        assert pc_state_map["pc1"]["position_x"] == event["final_x"]
        assert pc_state_map["pc1"]["position_y"] == event["final_y"]

    @pytest.mark.asyncio
    async def test_llm_waypoints_are_clamped_and_annotated(self):
        """LLM 返回的坐标会被裁剪到地图范围内，并附带旁白 / LLM waypoints clamped + narrated."""
        llm = AsyncMock()
        llm.call_structured = AsyncMock(
            return_value=ExploreOutputSchema(
                waypoints=[
                    ExploreWaypointSchema(x=999, y=-5, narration="发现一枚古币。"),
                    ExploreWaypointSchema(x=10, y=12, narration="草丛里有动静。"),
                ]
            )
        )
        config = {"configurable": {"llm": llm}}
        pc_state_map = {"pc1": {"position_x": 0, "position_y": 0}}
        scene_info = {
            "scene": {"map_width": 40, "map_height": 40},
            "pcs": [{"id": "pc1", "name": "pc1", "role": "adventurer"}],
        }
        event = await process_explore_action(
            decision={"type": "explore", "pc_id": "pc1"},
            scene_info=scene_info,
            pc_state_map=pc_state_map,
            config=config,
        )
        assert event["kind"] == "pc_explore"
        # 第一个坐标被裁剪 / First waypoint clamped
        assert event["waypoints"][0]["x"] == 39
        assert event["waypoints"][0]["y"] == 0
        assert event["waypoints"][0]["narration"] == "发现一枚古币。"
        # 原地踏步点（0,0）被跳过 / No-op skipped
        assert len(event["waypoints"]) == 2
        assert event["waypoints"][1]["x"] == 10
        assert event["waypoints"][1]["y"] == 12
