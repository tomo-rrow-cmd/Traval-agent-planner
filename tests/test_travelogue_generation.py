from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.agents.travelogue_agent import TravelogueAgent
from app.schemas.travelogue import TravelogueGenerateRequest


class FakeTravelogueLLM:
    def __init__(self):
        self.prompts: list[str] = []

    async def chat(self, messages, temperature=0.7):
        _ = temperature
        prompt = messages[0]["content"]
        self.prompts.append(prompt)
        if "起5个标题" in prompt:
            return "北京三日旅行手记"
        return "这是一段严格依据输入事实生成的可编辑游记初稿。"


def trip_info() -> dict:
    return {
        "destination": "北京",
        "total_days": 3,
        "actual_total_cost": 0,
        "daily_itinerary": [
            {"day": 1, "activities": [{"title": "天坛"}]},
            {"day": 2, "activities": [{"title": "故宫博物院"}, {"title": "景山公园"}]},
            {"day": 3, "activities": [{"title": "中国美术馆"}]},
        ],
    }


@pytest.mark.asyncio
async def test_zero_checkins_still_generates_all_plan_days():
    agent = TravelogueAgent(FakeTravelogueLLM())

    result = await agent.generate({
        "checkins": [],
        "style": "diary",
        "trip_info": trip_info(),
    })

    assert result["total_days"] == 3
    assert result["total_pois"] == 0
    assert result["total_cost"] == 0
    assert result["content"].count("## Day ") == 3
    assert "本日暂无实际签到记录" in result["content"]
    assert "# 北京三日旅行手记" not in result["content"]
    assert "总花费 ¥0" not in result["content"]


@pytest.mark.asyncio
async def test_partial_checkins_keep_actual_and_planned_facts_separate():
    llm = FakeTravelogueLLM()
    agent = TravelogueAgent(llm)
    agent.photo_organizer.select_cover = AsyncMock(return_value={
        "url": "/uploads/gugong.jpg",
    })
    context = trip_info()
    context["actual_total_cost"] = 60

    result = await agent.generate({
        "checkins": [{
            "source_day": 2,
            "poi_name": "故宫博物院",
            "note": "午门进入后很震撼",
            "rating": 5,
            "photos": [{"url": "/uploads/gugong.jpg", "ai_caption": "午门红墙"}],
            "actual_cost": 60,
        }],
        "style": "diary",
        "trip_info": context,
    })

    day_two_prompt = next(prompt for prompt in llm.prompts if "第 2 天" in prompt)
    assert "故宫博物院" in day_two_prompt
    assert "景山公园" in day_two_prompt
    assert "午门进入后很震撼" in day_two_prompt
    assert "只允许把“实际签到记录”写成已经发生的体验" in day_two_prompt
    assert "本日记录了 1 个实际打卡点" in result["content"]
    assert "### 实际记录" in result["content"]
    assert "午门进入后很震撼" in result["content"]
    assert result["total_cost"] == 60
    assert result["photos"] == ["/uploads/gugong.jpg"]


@pytest.mark.asyncio
async def test_generate_endpoint_reuses_existing_main_travelogue():
    from app.api.v1.travelogue import generate_travelogue

    existing = {
        "id": "travelogue-1", "trip_id": "trip-1", "user_id": "user-1",
        "title": "已有游记", "content": "## Day 1", "cover_url": None,
        "style": "diary", "photos": [], "total_days": 3, "total_pois": 1,
        "total_cost": 60, "total_photos": 0, "status": "draft",
        "created_at": None, "updated_at": None,
    }
    travelogue_service = MagicMock(
        get_by_trip=AsyncMock(return_value=existing),
        create=AsyncMock(),
        update=AsyncMock(),
    )
    trip_service = MagicMock(
        get_travelogue_context=AsyncMock(return_value={"checkins": []}),
    )

    response = await generate_travelogue(
        TravelogueGenerateRequest(trip_id="trip-1"),
        current_user={"user_id": "user-1"},
        travelogue_service=travelogue_service,
        trip_service=trip_service,
    )

    assert response.data["id"] == "travelogue-1"
    travelogue_service.create.assert_not_awaited()
    travelogue_service.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_published_main_travelogue_cannot_be_overwritten():
    from app.api.v1.travelogue import generate_travelogue

    existing = {
        "id": "travelogue-1", "trip_id": "trip-1", "user_id": "user-1",
        "status": "published",
    }
    travelogue_service = MagicMock(get_by_trip=AsyncMock(return_value=existing))
    trip_service = MagicMock(
        get_travelogue_context=AsyncMock(return_value={"checkins": []}),
    )

    with pytest.raises(HTTPException) as exc_info:
        await generate_travelogue(
            TravelogueGenerateRequest(trip_id="trip-1", regenerate=True),
            current_user={"user_id": "user-1"},
            travelogue_service=travelogue_service,
            trip_service=trip_service,
        )

    assert exc_info.value.status_code == 409
