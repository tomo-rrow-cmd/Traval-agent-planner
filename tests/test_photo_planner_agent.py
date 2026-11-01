"""测试 app/agents/photo_planner_agent.py — PhotoPlannerAgent"""

import pytest
from unittest.mock import patch, AsyncMock
from tests.test_llm import MockLLM
from app.agents.photo_planner_agent import PhotoPlannerAgent


@pytest.fixture
def agent():
    return PhotoPlannerAgent(MockLLM(api_key="test", base_url="http://test", model="test"))


class TestPhotoPlannerRun:
    @pytest.mark.asyncio
    async def test_no_images_returns_error(self, agent):
        result = await agent.run({"images": []})
        assert result["status"] == "no_images"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_no_images_key_returns_error(self, agent):
        result = await agent.run({})
        assert result["status"] == "no_images"

    @pytest.mark.asyncio
    async def test_vision_not_available_returns_fallback(self, agent):
        # 模拟 vision 不可用
        agent._vision = False  # 设置后 vision property 返回 None
        result = await agent.run({"images": ["https://example.com/photo.jpg"]})
        assert result["mode"] == "travel_planning"
        assert result["status"] == "collecting"
        assert result["ready"] is False
        assert "不太确定" in result["reply"]

    @pytest.mark.asyncio
    async def test_vision_available_extracts_preferences(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(return_value={
            "destination_hint": "桂林",
            "scene_summary": "山水风光很美",
            "preferences": ["自然风光", "徒步"],
            "pace": "悠闲",
            "vibe": "文艺",
        })
        agent._vision = mock_vision

        result = await agent.run({
            "images": ["https://example.com/photo.jpg"],
            "user_message": "想去这样的地方",
        })

        assert result["mode"] == "travel_planning"
        assert "桂林" in result["reply"]
        assert "自然风光" in result["reply"]
        assert result["extracted"]["preferences"] == ["自然风光", "徒步"]
        assert result["extracted"]["pace"] == "悠闲"
        assert result["extracted"]["preferences_provided"] is True
        assert result["image_count"] == 1

    @pytest.mark.asyncio
    async def test_vision_exception_is_caught(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(side_effect=RuntimeError("API Error"))
        agent._vision = mock_vision

        result = await agent.run({"images": ["https://example.com/photo.jpg"]})
        # 不应该抛出异常，应该回退到无 vision 状态
        assert "不太确定" in result["reply"]
        assert result["extracted"]["preferences_provided"] is False

    @pytest.mark.asyncio
    async def test_multiple_images_count_correctly(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(return_value={"preferences": ["摄影"]})
        agent._vision = mock_vision

        result = await agent.run({
            "images": ["img1.jpg", "img2.jpg", "img3.jpg"],
        })
        assert result["image_count"] == 3


class TestPhotoPlannerRunWithConfirm:
    @pytest.mark.asyncio
    async def test_all_params_ready(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(return_value={
            "preferences": ["美食"],
        })
        agent._vision = mock_vision

        result = await agent.run_with_confirm({
            "images": ["photo.jpg"],
            "destination": "成都",
            "origin": "北京",
            "days": 4,
            "total_budget": 6000,
        })

        assert result["ready"] is True
        assert result["confirmed"] is True
        assert result["extracted"]["destination"] == "成都"
        assert result["extracted"]["origin"] == "北京"
        assert result["extracted"]["days"] == 4
        assert result["extracted"]["total_budget"] == 6000

    @pytest.mark.asyncio
    async def test_incomplete_params_not_ready(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(return_value={"preferences": ["美食"]})
        agent._vision = mock_vision

        result = await agent.run_with_confirm({
            "images": ["photo.jpg"],
            "destination": "",
            "origin": "",
            "days": 3,
            "total_budget": 6000,
        })

        assert result["ready"] is False
        assert result["confirmed"] is False

    @pytest.mark.asyncio
    async def test_zero_budget_not_ready(self, agent):
        mock_vision = AsyncMock()
        mock_vision.extract_preferences = AsyncMock(return_value={})
        agent._vision = mock_vision

        result = await agent.run_with_confirm({
            "images": ["photo.jpg"],
            "destination": "上海",
            "origin": "北京",
            "days": 3,
            "total_budget": 0,
        })

        assert result["ready"] is False
