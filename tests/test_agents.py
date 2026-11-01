"""
Agent 测试
"""

import json
import inspect

import pytest

from app.agents.user_interaction_agent import UserInteractionAgent
from app.agents.attraction_agent import AttractionAgent
from app.agents.food_agent import FoodAgent
from app.agents import food_agent as food_module
from app.agents.hotel_agent import HotelAgent
from app.agents import hotel_agent as hotel_module
from app.agents.weather_agent import WeatherAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.traffic_agent import TrafficAgent
from app.agents import traffic_agent as traffic_module
from app.agents.route_optimizer_agent import RouteOptimizerAgent
from app.agents.souvenir_agent import SouvenirAgent
from app.services.third_party.railway12306 import PRICE_URL, Railway12306
from scripts.test_pipeline import _traffic_option_text, _train_fare

from tests.test_llm import MockLLM


@pytest.fixture
def mock_llm():
    return MockLLM(api_key="test", base_url="http://test", model="test")


class ScriptedLLM:
    def __init__(self, *responses: str):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        _ = temperature, max_tokens, kwargs
        self.calls.append(messages)
        return self.responses.pop(0) if self.responses else "好的"

    async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
        yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def chat_with_tools(self, messages, tools, temperature=0.7, **kwargs):
        _ = messages, tools, temperature, kwargs
        return {"content": "Mock tool response", "tool_calls": []}


def _agent_analysis(mode="travel_planning", extracted=None, ambiguous_fields=None):
    data = {
        "mode": mode,
        "extracted": {
            "destination": "",
            "origin": "",
            "start_date": "2026-08-01",
            "end_date": "",
            "days": 0,
            "total_budget": 0,
            "reserve_budget": 0,
            "planning_budget": 0,
            "budget_no_limit": False,
            "preferences": [],
            "cuisine_preferences": [],
            "preferred_transport": "地铁",
            "preferences_provided": False,
            "pace": "适中",
            "hotel_star": 3,
            "hotel_budget": 500,
            "meal_budget": 100,
            "travelers": 1,
        },
        "ambiguous_fields": ambiguous_fields or [],
    }
    if extracted:
        data["extracted"].update(extracted)
    return json.dumps(data, ensure_ascii=False)


def _completed_context():
    budget = {
        "total_budget": 1500,
        "reserve_budget": 200,
        "planning_budget": 1300,
    }
    trip_config = {
        "destination": "云南大理",
        "origin": "武汉",
        "start_date": "2026-09-01",
        "end_date": "2026-09-07",
        "days": 7,
        "total_budget": 1500,
        "reserve_budget": 200,
        "planning_budget": 1300,
        "budget_no_limit": False,
        "preferences": [],
        "cuisine_preferences": ["云南菜"],
        "preferred_transport": "步行",
        "preferred_transport_provided": True,
        "preferences_provided": True,
        "pace": "轻松",
        "hotel_star": 4,
        "hotel_budget": 300,
        "meal_budget": 80,
        "travelers": 2,
        "budget": budget,
    }
    return {
        "session_status": "completed",
        "latest_plan_id": "run-1",
        "plan_run_count": 1,
        "latest_plan_summary": {
            "destination": "云南大理",
            "origin": "武汉",
            "start_date": "2026-09-01",
            "end_date": "2026-09-07",
            "days": 7,
            "preferences": [],
            "cuisine_preferences": ["云南菜"],
            "preferred_transport": "步行",
            "preferred_transport_provided": True,
            "preferences_provided": True,
            "pace": "轻松",
            "hotel_star": 4,
            "hotel_budget": 300,
            "meal_budget": 80,
            "travelers": 2,
            "budget": budget,
            "trip_config": trip_config,
        },
    }


def _qingdao_completed_context():
    budget = {
        "total_budget": 1000,
        "reserve_budget": 0,
        "planning_budget": 1000,
    }
    trip_config = {
        "destination": "青岛",
        "origin": "麻城",
        "start_date": "2026-10-01",
        "end_date": "2026-10-05",
        "days": 5,
        "total_budget": 1000,
        "reserve_budget": 0,
        "planning_budget": 1000,
        "budget_no_limit": False,
        "preferences": ["轻松慢游"],
        "cuisine_preferences": ["海鲜"],
        "preferred_transport": "打车",
        "preferences_provided": True,
        "pace": "轻松",
        "hotel_star": 3,
        "hotel_budget": 500,
        "meal_budget": 100,
        "travelers": 1,
        "budget": budget,
    }
    return {
        "session_status": "completed",
        "latest_plan_id": "run-qingdao",
        "plan_run_count": 1,
        "latest_plan_summary": {
            "destination": "青岛",
            "origin": "麻城",
            "start_date": "2026-10-01",
            "end_date": "2026-10-05",
            "days": 5,
            "preferences": ["轻松慢游"],
            "cuisine_preferences": ["海鲜"],
            "preferred_transport": "打车",
            "preferences_provided": True,
            "pace": "轻松",
            "hotel_star": 3,
            "hotel_budget": 500,
            "meal_budget": 100,
            "travelers": 1,
            "budget": budget,
            "trip_config": trip_config,
        },
    }


@pytest.mark.asyncio
async def test_user_interaction_agent(mock_llm):
    agent = UserInteractionAgent(mock_llm)
    result = await agent.run({"message": "帮我规划北京3天行程", "history": [], "context": {}})
    assert "reply" in result
    assert "extracted" in result


@pytest.mark.asyncio
async def test_user_interaction_agent_daily_chat_does_not_plan():
    llm = ScriptedLLM(
        _agent_analysis(mode="daily_chat"),
        "当然可以。需要规划旅行时，我也可以继续帮你整理出行信息。",
    )
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "给我讲个冷笑话", "history": [], "context": {}})

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert "冷笑话" in result["reply"] or "旅行" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_missing_required_fields_not_ready():
    llm = ScriptedLLM(_agent_analysis(
        extracted={"destination": "北京", "days": 3},
    ))
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "帮我规划北京3天行程", "history": [], "context": {}})

    assert result["mode"] == "travel_planning"
    assert result["status"] == "collecting"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == ["origin", "total_budget", "preferences"]
    assert result["requested_fields"] == ["total_budget", "preferences"]
    assert "总预算" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_no_preference_counts_as_provided():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "北京",
        "origin": "上海",
        "days": 3,
        "total_budget": 5000,
        "preferences": [],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "从上海出发去北京玩3天，预算5000，无偏好",
        "history": [],
        "context": {},
    })

    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["missing_fields"] == []
    assert result["extracted"]["preferences"] == []
    assert result["extracted"]["preferences_provided"] is True
    assert "偏好 无偏好" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_complete_info_asks_for_confirmation_first():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "北京",
        "origin": "上海",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["美食"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "从上海出发去北京玩3天，预算5000，喜欢美食",
        "history": [],
        "context": {},
    })

    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_start_date_and_days_derives_end_date():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "2026-08-10",
        "days": 4,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "8月10日从武汉去成都玩4天，预算5000，喜欢历史文化",
        "history": [],
        "context": {},
    })

    assert result["status"] == "awaiting_confirmation"
    assert result["extracted"]["start_date"] == "2026-08-10"
    assert result["extracted"]["end_date"] == "2026-08-13"
    assert result["extracted"]["days"] == 4


@pytest.mark.asyncio
async def test_user_interaction_agent_start_and_end_dates_derive_days():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "2026-08-10",
        "end_date": "2026-08-14",
        "days": 0,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "8月10日至8月14日从武汉去成都，预算5000，喜欢历史文化",
        "history": [],
        "context": {},
    })

    assert result["status"] == "awaiting_confirmation"
    assert result["extracted"]["days"] == 5


@pytest.mark.asyncio
async def test_user_interaction_agent_date_range_and_days_conflict_collects():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "2026-08-10",
        "end_date": "2026-08-14",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "8月10日至14日从武汉去成都玩3天，预算5000，喜欢历史文化",
        "history": [],
        "context": {},
    })

    assert result["status"] == "collecting"
    assert result["ready"] is False
    assert "日期范围代表 5 天" in result["reply"]
    assert "填写的是 3 天" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_missing_start_date_is_asked_first():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "",
        "days": 4,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "从武汉去成都玩4天，预算5000，喜欢历史文化",
        "history": [],
        "context": {},
    })

    assert result["status"] == "collecting"
    assert result["missing_fields"] == ["start_date"]
    assert "具体出发日期" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_splits_cuisine_and_transport_preferences():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "2026-08-10",
        "days": 4,
        "total_budget": 5000,
        "preferences": ["历史文化", "川菜"],
        "preferences_provided": True,
        "preferred_transport": "尽量步行",
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "8月10日从武汉去成都玩4天，预算5000，喜欢历史文化，想吃川菜，尽量步行",
        "history": [],
        "context": {},
    })

    extracted = result["extracted"]
    assert extracted["preferences"] == ["历史文化"]
    assert extracted["cuisine_preferences"] == ["川菜"]
    assert extracted["preferred_transport"] == "步行"
    assert extracted["preferences_provided"] is True
    assert "菜系 川菜" in result["reply"]
    assert "交通 步行" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_confirmation_with_date_revision_not_confirmed():
    confirmation = (
        "我理解的信息是：从 武汉 出发，去 成都，日期 2026-08-10 至 2026-08-13，"
        "玩 4 天，预算 ¥5000，偏好 历史文化，菜系 川菜，交通 步行。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "成都",
        "origin": "武汉",
        "start_date": "2026-08-20",
        "days": 4,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "cuisine_preferences": ["川菜"],
        "preferences_provided": True,
        "preferred_transport": "步行",
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "确认，不过改成8月20日出发",
        "history": [
            {"role": "user", "content": "8月10日从武汉去成都玩4天，预算5000，喜欢历史文化，想吃川菜，尽量步行"},
            {"role": "assistant", "content": confirmation},
            {"role": "user", "content": "确认，不过改成8月20日出发"},
        ],
        "context": {},
    })

    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["extracted"]["start_date"] == "2026-08-20"


@pytest.mark.asyncio
async def test_user_interaction_agent_positive_reply_without_confirmation_gate_not_ready():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "北京",
        "origin": "上海",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["美食"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "可以", "history": [], "context": {}})

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False
    assert result["confirmed"] is False


@pytest.mark.asyncio
async def test_user_interaction_agent_travel_wish_stays_daily_chat():
    llm = ScriptedLLM(
        _agent_analysis(mode="travel_planning", extracted={"destination": "北京"}),
        "北京确实很适合慢慢逛，你更期待历史街区还是城市风景？",
    )
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "我想去北京玩诶", "history": [], "context": {}})

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False


@pytest.mark.asyncio
async def test_user_interaction_agent_uses_natural_collection_question():
    llm = ScriptedLLM(
        _agent_analysis(extracted={"destination": "北京", "start_date": ""}),
        json.dumps({
            "reply": "北京安排上啦～你准备从哪儿出发，大概哪天走？",
            "requested_fields": ["origin", "start_date"],
        }, ensure_ascii=False),
    )
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "帮我规划北京行程", "history": [], "context": {}})

    assert result["status"] == "collecting"
    assert result["requested_fields"] == ["origin", "start_date"]
    assert result["reply"] == "北京安排上啦～你准备从哪儿出发，大概哪天走？"


@pytest.mark.asyncio
async def test_user_interaction_agent_rejects_invalid_collection_fields():
    llm = ScriptedLLM(
        _agent_analysis(extracted={"destination": "北京", "start_date": ""}),
        json.dumps({
            "reply": "先告诉我酒店名字。",
            "requested_fields": ["hotel_name"],
        }, ensure_ascii=False),
    )
    agent = UserInteractionAgent(llm)

    result = await agent.run({"message": "帮我规划北京行程", "history": [], "context": {}})

    assert result["status"] == "collecting"
    assert result["requested_fields"] == ["start_date", "days"]
    assert "哪天出发" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_continues_natural_collection_from_metadata():
    llm = ScriptedLLM(
        _agent_analysis(extracted={
            "destination": "北京",
            "origin": "武汉",
            "start_date": "",
        }),
        json.dumps({
            "reply": "从武汉出发没问题。你大概哪天走，准备玩几天？",
            "requested_fields": ["start_date", "days"],
        }, ensure_ascii=False),
    )
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "武汉",
        "history": [
            {"role": "user", "content": "帮我规划北京行程"},
            {
                "role": "assistant",
                "content": "北京安排上啦～你准备从哪儿出发？",
                "metadata": {
                    "agent_status": "collecting",
                    "requested_fields": ["origin"],
                },
            },
            {"role": "user", "content": "武汉"},
        ],
        "context": {},
    })

    assert result["mode"] == "travel_planning"
    assert result["status"] == "collecting"
    assert result["requested_fields"] == ["start_date", "days"]


@pytest.mark.asyncio
async def test_user_interaction_agent_bare_en_confirms_after_gate():
    confirmation = (
        "我理解的信息是：从 武汉 出发，去 北京，日期 2099-08-01 至 2099-08-03，"
        "玩 3 天，预算 ¥5000，偏好 历史文化，菜系 无。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "北京",
        "origin": "武汉",
        "start_date": "2099-08-01",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "嗯",
        "history": [
            {"role": "assistant", "content": confirmation},
            {"role": "user", "content": "嗯"},
        ],
        "context": {},
    })

    assert result["status"] == "confirmed"
    assert result["confirmed"] is True
    assert result["ready"] is True


def test_user_interaction_agent_confirmation_hides_default_transport():
    extracted = UserInteractionAgent._normalize_extracted({
        "destination": "北京",
        "origin": "武汉",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["历史文化"],
        "preferences_provided": True,
        "preferred_transport": "地铁",
    })

    hidden = UserInteractionAgent._confirmation_reply(extracted)
    shown = UserInteractionAgent._confirmation_reply({
        **extracted,
        "preferred_transport": "步行",
        "preferred_transport_provided": True,
    })

    assert "交通 地铁" not in hidden
    assert "交通 步行" in shown


@pytest.mark.asyncio
async def test_user_interaction_agent_confirmed_after_confirmation_gate_ready():
    confirmation = (
        "我理解的信息是：从 上海 出发，去 北京，玩 3 天，预算 ¥5000，偏好 美食。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "北京",
        "origin": "上海",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["美食"],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "确认，开始规划",
        "history": [
            {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
            {"role": "assistant", "content": confirmation},
            {"role": "user", "content": "确认，开始规划"},
        ],
        "context": {},
    })

    assert result["status"] == "confirmed"
    assert result["ready"] is True
    assert result["confirmed"] is True


@pytest.mark.asyncio
async def test_user_interaction_agent_confirmation_restores_dates_cuisine_and_transport():
    confirmation = (
        "我理解的信息是：从 武汉 出发，去 成都，日期 2026-09-10 至 2026-09-13，"
        "玩 4 天，预算 ¥5000，偏好 历史文化，菜系 川菜，交通 步行。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "",
        "origin": "",
        "start_date": "",
        "end_date": "",
        "days": 0,
        "total_budget": 0,
        "preferences": [],
        "cuisine_preferences": [],
        "preferred_transport": "地铁",
        "preferences_provided": False,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "确认，开始规划",
        "history": [
            {"role": "assistant", "content": confirmation},
            {"role": "user", "content": "确认，开始规划"},
        ],
        "context": {},
    })

    assert result["ready"] is True
    assert result["extracted"]["start_date"] == "2026-09-10"
    assert result["extracted"]["end_date"] == "2026-09-13"
    assert result["extracted"]["days"] == 4
    assert result["extracted"]["cuisine_preferences"] == ["川菜"]
    assert result["extracted"]["preferred_transport"] == "步行"


@pytest.mark.asyncio
async def test_user_interaction_agent_completed_session_chat_stays_daily():
    llm = ScriptedLLM("你好呀，今天想聊点什么？")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "你好",
        "history": [
            {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 上海 出发，去 北京，玩 3 天，预算 ¥5000，偏好 美食。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "确认，开始规划"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": {"session_status": "completed", "latest_plan_id": "run-1", "plan_run_count": 1},
    })

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False
    assert result["reply"] == "你好呀，今天想聊点什么？"
    assert len(llm.calls) == 1
    assert llm.calls[0][0]["role"] == "system"


@pytest.mark.asyncio
async def test_user_interaction_agent_completed_simple_destination_wish_stays_daily():
    llm = ScriptedLLM("东北可以先作为备选方向，我们可以先聊聊你更想看雪景还是海边。")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "我还想去东北",
        "history": [
            {"role": "user", "content": "从武汉出发去云南大理玩7天，预算1500，留200应急，无偏好"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 武汉 出发，去 云南大理，玩 7 天，"
                "预算 总预算 ¥1500，其中 ¥200 留作应急，本次按 ¥1300 安排行程，偏好 无偏好。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "确认，开始规划"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _completed_context(),
    })

    assert result["mode"] == "daily_chat"
    assert result["ready"] is False
    assert len(llm.calls) == 1
    assert llm.calls[0][0]["role"] == "system"
    assert "完整对话" not in llm.calls[0][0]["content"]


@pytest.mark.asyncio
async def test_user_interaction_agent_completed_dali_wish_stays_daily():
    llm = ScriptedLLM("大理也挺适合慢慢逛，可以先想想你更期待洱海还是古城。")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "哎呀，我现在又想去云南大理",
        "history": [
            {"role": "user", "content": "从麻城出发去青岛玩5天，总预算1000，偏好轻松慢游"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False
    assert len(llm.calls) == 1
    assert llm.calls[0][0]["role"] == "system"


@pytest.mark.asyncio
async def test_user_interaction_agent_replan_destination_change_inherits_full_config():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "那你重新生成行程吧，目的地变成大理，其他沿用相同配置",
        "history": [
            {"role": "user", "content": "从麻城出发去青岛玩5天，总预算1000，偏好轻松慢游"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
            {"role": "user", "content": "哎呀，我现在又想去云南大理"},
            {"role": "assistant", "content": "大理也挺适合慢慢逛。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "大理"
    assert extracted["origin"] == "麻城"
    assert extracted["start_date"] == "2026-10-01"
    assert extracted["end_date"] == "2026-10-05"
    assert extracted["days"] == 5
    assert extracted["total_budget"] == 1000
    assert extracted["reserve_budget"] == 0
    assert extracted["planning_budget"] == 1000
    assert extracted["preferences"] == ["轻松慢游"]
    assert extracted["cuisine_preferences"] == ["海鲜"]
    assert extracted["preferred_transport"] == "打车"
    assert extracted["preferences_provided"] is True
    assert extracted["pace"] == "轻松"
    assert extracted["hotel_star"] == 3
    assert extracted["hotel_budget"] == 500
    assert extracted["meal_budget"] == 100
    assert extracted["travelers"] == 1
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]
    assert "青岛" not in llm.calls[0][0]["content"]


@pytest.mark.asyncio
async def test_user_interaction_agent_replan_cuisine_change_keeps_travel_preferences():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat", extracted={
        "start_date": "",
        "cuisine_preferences": ["粤菜"],
        "preferences": [],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "菜系改成粤菜，其他沿用，重新规划",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["status"] == "awaiting_confirmation"
    assert extracted["preferences"] == ["轻松慢游"]
    assert extracted["cuisine_preferences"] == ["粤菜"]
    assert extracted["preferred_transport"] == "打车"
    assert extracted["start_date"] == "2026-10-01"
    assert extracted["end_date"] == "2026-10-05"


@pytest.mark.asyncio
@pytest.mark.parametrize(("message", "changed", "expected"), [
    (
        "出发日期改成2026-10-10，其他沿用，重新规划",
        {"start_date": "2026-10-10", "end_date": "", "days": 0},
        ("2026-10-10", "2026-10-14", 5),
    ),
    (
        "返程日期改成2026-10-07，其他沿用，重新规划",
        {"start_date": "", "end_date": "2026-10-07", "days": 0},
        ("2026-10-01", "2026-10-07", 7),
    ),
    (
        "行程改成3天，其他沿用，重新规划",
        {"start_date": "", "end_date": "", "days": 3},
        ("2026-10-01", "2026-10-03", 3),
    ),
])
async def test_user_interaction_agent_replan_recomputes_changed_date_fields(
    message,
    changed,
    expected,
):
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat", extracted=changed))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": message,
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["status"] == "awaiting_confirmation"
    assert (
        extracted["start_date"], extracted["end_date"], extracted["days"]
    ) == expected


@pytest.mark.asyncio
async def test_user_interaction_agent_old_plan_without_date_asks_date_and_keeps_config():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat", extracted={
        "start_date": "",
        "end_date": "",
        "days": 0,
        "preferences": [],
        "preferences_provided": False,
    }))
    agent = UserInteractionAgent(llm)
    context = _qingdao_completed_context()
    context["latest_plan_summary"].pop("start_date")
    context["latest_plan_summary"].pop("end_date")
    context["latest_plan_summary"]["trip_config"].pop("start_date")
    context["latest_plan_summary"]["trip_config"].pop("end_date")

    result = await agent.run({
        "message": "目的地改成大理，其他沿用，重新规划",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": context,
    })

    assert result["status"] == "collecting"
    assert result["missing_fields"] == ["start_date"]
    assert result["extracted"]["start_date"] == ""
    assert result["extracted"]["total_budget"] == 1000
    assert result["extracted"]["preferences"] == ["轻松慢游"]


@pytest.mark.asyncio
async def test_user_interaction_agent_real_transcript_yunnan_typo_replan_asks_confirmation():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "去云南吧，其他部分和之前相同，你帮我重新生辰生成一下",
        "history": [
            {"role": "user", "content": "我想从武汉 去北京，预算1000，时间大概4天，你帮我规划一下"},
            {"role": "assistant", "content": "你有什么旅行偏好吗？"},
            {"role": "user", "content": "轻松漫游吧"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 武汉 出发，去 北京，玩 4 天，预算 ¥1000，偏好 轻松漫游。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "对的，开始规划吧"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
            {"role": "user", "content": "哎呀，现在 又想去云南了，"},
            {"role": "assistant", "content": "云南可以先聊聊，想正式规划时直接说重新规划。"},
        ],
        "context": {
            "session_status": "completed",
            "latest_plan_id": "run-beijing",
            "plan_run_count": 1,
                "latest_plan_summary": {
                    "destination": "北京",
                    "origin": "武汉",
                    "start_date": "2099-11-01",
                    "end_date": "2099-11-04",
                    "days": 4,
                "preferences": ["轻松漫游"],
                "preferences_provided": True,
                "pace": "轻松",
                "hotel_star": 3,
                "hotel_budget": 500,
                "meal_budget": 100,
                "travelers": 1,
                "budget": {
                    "total_budget": 1000,
                    "reserve_budget": 0,
                    "planning_budget": 1000,
                },
            },
        },
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "云南"
    assert extracted["origin"] == "武汉"
    assert extracted["days"] == 4
    assert extracted["total_budget"] == 1000
    assert extracted["planning_budget"] == 1000
    assert extracted["preferences"] == ["轻松漫游"]
    assert extracted["preferences_provided"] is True
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_inherited_field_clears_ambiguous_missing():
    llm = ScriptedLLM(_agent_analysis(
        extracted={"destination": "云南昆明"},
        ambiguous_fields=["origin"],
    ))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "去云南昆明，其他部分不 变，重新规划一下",
        "history": [
            {"role": "user", "content": "从武汉去北京，预算2000，7天，轻松漫游"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 武汉 出发，去 北京，玩 7 天，预算 ¥2000，偏好 轻松漫游。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "对的"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
            {"role": "user", "content": "欸，突然感觉好热，想去别的清凉地方"},
            {"role": "assistant", "content": "确实，北京夏天热起来挺难熬的。可以换个清凉地方。"},
        ],
        "context": {
            "session_status": "completed",
            "latest_plan_id": "run-beijing",
            "plan_run_count": 1,
                "latest_plan_summary": {
                    "destination": "北京",
                    "origin": "武汉",
                    "start_date": "2099-11-01",
                    "end_date": "2099-11-07",
                    "days": 7,
                "preferences": ["轻松漫游"],
                "preferences_provided": True,
                "pace": "轻松",
                "hotel_star": 3,
                "hotel_budget": 500,
                "meal_budget": 100,
                "travelers": 1,
                "budget": {
                    "total_budget": 2000,
                    "reserve_budget": 0,
                    "planning_budget": 2000,
                },
            },
        },
    })

    extracted = result["extracted"]
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert "哪个城市出发" not in result["reply"]
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]
    assert extracted["destination"] == "云南昆明"
    assert extracted["origin"] == "武汉"
    assert extracted["days"] == 7
    assert extracted["total_budget"] == 2000
    assert extracted["preferences"] == ["轻松漫游"]


@pytest.mark.asyncio
async def test_user_interaction_agent_replan_confirmation_gate_then_ready():
    confirmation = (
        "我理解的信息是：从 武汉 出发，去 云南，玩 7 天，预算 ¥2000，偏好 轻松漫游。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "确认，开始规划",
        "history": [
            {"role": "user", "content": "从武汉去北京，预算2000，7天，轻松漫游"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 武汉 出发，去 北京，玩 7 天，预算 ¥2000，偏好 轻松漫游。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "对的"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
            {"role": "user", "content": "去云南吧，其他部分和之前相同，你帮我重新生成一下"},
            {"role": "assistant", "content": confirmation},
        ],
        "context": {
            "session_status": "completed",
            "latest_plan_id": "run-beijing",
            "plan_run_count": 1,
            "latest_plan_summary": {
                "destination": "北京",
                "origin": "武汉",
                "days": 7,
                "preferences": ["轻松漫游"],
                "preferences_provided": True,
                "pace": "慢",
                "hotel_star": 3,
                "hotel_budget": 500,
                "meal_budget": 100,
                "travelers": 1,
                "budget": {
                    "total_budget": 2000,
                    "reserve_budget": 0,
                    "planning_budget": 2000,
                },
            },
        },
    })

    extracted = result["extracted"]
    assert result["status"] == "confirmed"
    assert result["ready"] is True
    assert result["confirmed"] is True
    assert extracted["destination"] == "云南"
    assert extracted["origin"] == "武汉"
    assert extracted["days"] == 7
    assert extracted["total_budget"] == 2000


@pytest.mark.asyncio
async def test_user_interaction_agent_real_transcript_dali_abbrev_replan_asks_confirmation():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "去大理，其还是一样，帮我重新生成",
        "history": [
            {"role": "user", "content": "从武汉出发去北京玩4天，预算1000，喜欢轻松漫游"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 武汉 出发，去 北京，玩 4 天，预算 ¥1000，偏好 轻松漫游。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "对的，开始规划吧"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": {
            "session_status": "completed",
            "latest_plan_id": "run-beijing",
            "plan_run_count": 1,
                "latest_plan_summary": {
                    "destination": "北京",
                    "origin": "武汉",
                    "start_date": "2099-11-01",
                    "end_date": "2099-11-04",
                    "days": 4,
                "preferences": ["轻松漫游"],
                "preferences_provided": True,
                "budget": {
                    "total_budget": 1000,
                    "reserve_budget": 0,
                    "planning_budget": 1000,
                },
            },
        },
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "大理"
    assert extracted["origin"] == "武汉"
    assert extracted["days"] == 4
    assert extracted["total_budget"] == 1000
    assert extracted["preferences"] == ["轻松漫游"]
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_destination_change_other_parts_same_asks_confirmation():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "目的地变成大理，其他部分和之前一样",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "大理"
    assert extracted["origin"] == "麻城"
    assert extracted["days"] == 5
    assert extracted["total_budget"] == 1000
    assert extracted["preferences"] == ["轻松慢游"]
    assert extracted["preferences_provided"] is True
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_destination_change_other_parts_same_replan_asks_confirmation():
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "目的地变成大理，其他部分和之前一样，重新规划一下",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "大理"
    assert extracted["origin"] == "麻城"
    assert extracted["days"] == 5
    assert extracted["total_budget"] == 1000
    assert extracted["preferences"] == ["轻松慢游"]
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_replan_this_inherits_latest_confirmation():
    confirmation = (
        "我理解的信息是：从 上海 出发，去 北京，日期 2099-12-01 至 2099-12-03，"
        "玩 3 天，预算 ¥5000，偏好 美食，菜系 无，交通 地铁。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    llm = ScriptedLLM(_agent_analysis(mode="daily_chat"))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "不管，你就按照这个重新规划一下",
        "history": [
            {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
            {"role": "assistant", "content": confirmation},
            {"role": "user", "content": "确认，开始规划"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _qingdao_completed_context(),
    })

    extracted = result["extracted"]
    assert result["mode"] == "travel_planning"
    assert result["status"] == "awaiting_confirmation"
    assert result["ready"] is False
    assert result["confirmed"] is False
    assert result["missing_fields"] == []
    assert extracted["destination"] == "北京"
    assert extracted["origin"] == "上海"
    assert extracted["days"] == 3
    assert extracted["total_budget"] == 5000
    assert extracted["preferences"] == ["美食"]
    assert "确认后我再开始生成完整方案，可以吗？" in result["reply"]


@pytest.mark.asyncio
async def test_user_interaction_agent_completed_abandon_old_destination_stays_latest_topic():
    llm = ScriptedLLM("好，那就先不考虑云南，东北这个方向可以继续聊。")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "那先放弃云南吧",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
            {"role": "user", "content": "我还想去东北"},
            {"role": "assistant", "content": "东北可以先作为备选方向，我们可以慢慢比较。"},
        ],
        "context": _completed_context(),
    })

    system_text = "\n".join(
        message["content"] for message in llm.calls[0]
        if message.get("role") == "system"
    )
    assert result["mode"] == "daily_chat"
    assert result["ready"] is False
    assert len(llm.calls) == 1
    assert "不要进入结构化规划" in system_text
    assert "围绕最新话题" in system_text
    assert "如果仍按之前条件" in system_text


@pytest.mark.asyncio
async def test_user_interaction_agent_chat_confirmation_after_unstructured_plan_not_generated():
    llm = ScriptedLLM("不应该调用闲聊模型生成方案")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "可以",
        "history": [
            {"role": "assistant", "content": "如果你确认可以，我现在就生成详细行程。"},
            {"role": "user", "content": "可以"},
        ],
        "context": _qingdao_completed_context(),
    })

    assert result["mode"] == "daily_chat"
    assert result["status"] == "chat"
    assert result["ready"] is False
    assert "正式生成方案需要先进入规划流程" in result["reply"]
    assert llm.calls == []


@pytest.mark.asyncio
async def test_user_interaction_agent_completed_explicit_replan_enters_collection():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "东北",
        "days": 5,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "重新规划东北5天",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": _completed_context(),
    })

    assert result["mode"] == "travel_planning"
    assert result["status"] == "collecting"
    assert result["ready"] is False
    assert result["missing_fields"] == ["origin", "total_budget", "preferences"]
    assert result["requested_fields"] == ["total_budget", "preferences"]


@pytest.mark.asyncio
async def test_user_interaction_agent_new_plan_resets_previous_slots():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "杭州",
        "origin": "上海",
        "days": 2,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "我还想再规划一个从上海去杭州的周末游",
        "history": [
            {"role": "user", "content": "从北京出发去武汉玩7天，预算1000，无偏好"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 北京 出发，去 武汉，玩 7 天，预算 ¥1000，偏好 无偏好。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "确认，开始规划"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": {"session_status": "completed", "latest_plan_id": "run-1", "plan_run_count": 1},
    })

    assert result["mode"] == "travel_planning"
    assert result["extracted"]["origin"] == "上海"
    assert result["extracted"]["destination"] == "杭州"
    assert result["extracted"]["days"] == 2
    assert result["extracted"]["total_budget"] == 0
    assert result["missing_fields"] == ["total_budget", "preferences"]
    assert "北京" not in llm.calls[0][0]["content"]
    assert "武汉" not in llm.calls[0][0]["content"]


@pytest.mark.asyncio
async def test_user_interaction_agent_inherits_only_requested_budget():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "长沙",
        "origin": "武汉",
        "days": 3,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "沿用上次预算，再规划一个武汉到长沙 3 天",
        "history": [
            {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
            {"role": "assistant", "content": (
                "我理解的信息是：从 上海 出发，去 北京，玩 3 天，预算 ¥5000，偏好 美食。"
                "确认后我再开始生成完整方案，可以吗？"
            )},
            {"role": "user", "content": "确认，开始规划"},
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": {"session_status": "completed", "latest_plan_id": "run-1", "plan_run_count": 1},
    })

    assert result["extracted"]["origin"] == "武汉"
    assert result["extracted"]["destination"] == "长沙"
    assert result["extracted"]["total_budget"] == 5000
    assert result["extracted"]["planning_budget"] == 5000
    assert result["extracted"]["preferences"] == []
    assert result["extracted"]["preferences_provided"] is False
    assert result["missing_fields"] == ["preferences"]


@pytest.mark.asyncio
async def test_user_interaction_agent_city_question_after_completion_is_chat():
    llm = ScriptedLLM("武汉很适合慢慢逛，东湖、省博、江滩都值得看看。")
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "武汉有哪些景点",
        "history": [
            {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
        ],
        "context": {"session_status": "completed", "latest_plan_id": "run-1", "plan_run_count": 1},
    })

    assert result["mode"] == "daily_chat"
    assert result["ready"] is False
    assert result["reply"].startswith("武汉")


@pytest.mark.asyncio
async def test_user_interaction_agent_reserve_budget_reduces_planning_budget():
    llm = ScriptedLLM(_agent_analysis(extracted={
        "destination": "武汉",
        "origin": "北京",
        "days": 7,
        "total_budget": 1000,
        "preferences": [],
        "preferences_provided": True,
    }))
    agent = UserInteractionAgent(llm)

    result = await agent.run({
        "message": "从北京去武汉玩7天，预算1000，留200应急，无偏好",
        "history": [],
        "context": {},
    })

    assert result["extracted"]["total_budget"] == 1000
    assert result["extracted"]["reserve_budget"] == 200
    assert result["extracted"]["planning_budget"] == 800
    assert "留作应急" in result["reply"]
    assert "按 ¥800 安排行程" in result["reply"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_attraction_agent(mock_llm):
    agent = AttractionAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "days": 3,
        "preferences": ["历史人文", "美食"],
    })
    assert "attractions" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_food_agent(mock_llm):
    agent = FoodAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "cuisine_preferences": ["川菜", "烤鸭"],
        "meal_budget": 100,
    })
    assert "restaurants" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hotel_agent(mock_llm):
    agent = HotelAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "hotel_star_min": 3,
        "budget_per_night": 500,
    })
    assert "hotels" in result


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.integration
async def test_weather_agent(mock_llm):
    agent = WeatherAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "start_date": "2026-07-10",
        "end_date": "2026-07-12",
    })
    assert "weather_data" in result


@pytest.mark.asyncio
async def test_budget_agent(mock_llm):
    agent = BudgetAgent(mock_llm)
    daily_itinerary = [{"day": 1, "attractions": [{"name": "故宫博物院"}]}]
    result = await agent.run({
        "total_budget": 5000,
        "reserve_budget": 500,
        "planning_budget": 4500,
        "days": 3,
        "travelers": 2,
        "destination": "北京",
        "origin": "上海",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "preferences": ["美食"],
        "cuisine_preferences": ["川菜"],
        "preferred_transport": "步行",
        "preferred_transport_provided": True,
        "preferences_provided": True,
        "pace": "轻松",
        "hotel_star": 4,
        "hotel_budget": 800,
        "meal_budget": 120,
        "daily_itinerary": daily_itinerary,
    })
    assert "budget_plan" in result
    assert result["final_plan"]["daily_itinerary"] == daily_itinerary
    assert result["final_plan"]["daily_plan"] == daily_itinerary
    assert result["final_plan"]["start_date"] == "2099-08-01"
    assert result["final_plan"]["end_date"] == "2099-08-03"
    assert result["final_plan"]["cuisine_preferences"] == ["川菜"]
    assert result["final_plan"]["preferred_transport"] == "步行"
    assert result["final_plan"]["trip_config"] == {
        "destination": "北京",
        "origin": "上海",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "days": 3,
        "total_budget": 5000,
        "reserve_budget": 500,
        "planning_budget": 4500,
        "budget_no_limit": False,
        "preferences": ["美食"],
        "cuisine_preferences": ["川菜"],
        "preferred_transport": "步行",
        "preferred_transport_provided": True,
        "preferences_provided": True,
        "pace": "轻松",
        "hotel_star": 4,
        "hotel_budget": 800,
        "meal_budget": 120,
        "travelers": 2,
        "budget": {
            "total_budget": 5000,
            "reserve_budget": 500,
            "planning_budget": 4500,
        },
    }
    assert result["budget_plan"]["total_budget"] == 5000
    assert result["budget_plan"]["reserve_budget"] == 500
    assert result["budget_plan"]["planning_budget"] == 4500


@pytest.mark.asyncio
async def test_traffic_agent(mock_llm):
    agent = TrafficAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "daily_locations": [],
        "preferred_transport": "地铁",
    })
    assert "traffic_plan" in result


@pytest.mark.asyncio
async def test_traffic_agent_skips_duplicate_locations(mock_llm, monkeypatch):
    class FailAmap:
        async def route_planning(self, origin, destination, route_type="transit", city=None):
            _ = origin, destination, route_type, city
            raise AssertionError("duplicate locations should not request routing")

    monkeypatch.setattr("app.agents.traffic_agent.AmapService", lambda: FailAmap())
    agent = TrafficAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "daily_locations": [{
            "day": 1,
            "attractions": [
                {"name": "国家植物园北园", "latitude": 39.99, "longitude": 116.21},
                {"name": "国家植物园北园", "latitude": 39.99, "longitude": 116.21},
                {"name": "植物园北门", "latitude": 39.99, "longitude": 116.21},
            ],
        }],
    })

    day = result["daily_traffic"][0]
    assert day["segments"] == []
    assert day["total_time_min"] == 0
    assert day["total_cost"] == 0
    assert result["total_traffic_cost"] == 0


@pytest.mark.asyncio
async def test_traffic_agent_adds_route_options(mock_llm, monkeypatch):
    route_calls = []

    class FakeAmap:
        async def route_planning(self, origin, destination, route_type="transit", city=None):
            _ = origin, destination
            route_calls.append((route_type, city))
            if route_type == "transit":
                return {
                    "transits": [{
                        "duration": "2700",
                        "cost": "2",
                        "distance": "3400",
                        "segments": [
                            {"walking": {"distance": "600"}},
                            {"bus": {"buslines": [{"name": "地铁1号线(苹果园--环球度假区)"}]}},
                            {"walking": {"distance": "900"}},
                        ],
                    }]
                }
            if route_type == "walking":
                return {"paths": [{"duration": "2280", "distance": "3200"}]}
            return {"taxi_cost": "18", "paths": [{"duration": "1080", "distance": "3400"}]}

    monkeypatch.setattr("app.agents.traffic_agent.AmapService", lambda: FakeAmap())
    agent = TrafficAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "daily_locations": [{
            "day": 1,
            "attractions": [
                {"name": "天安门广场", "latitude": 39.9087, "longitude": 116.3975},
                {"name": "故宫博物院", "latitude": 39.9163, "longitude": 116.3972},
            ],
        }],
    })

    segment = result["daily_traffic"][0]["segments"][0]
    assert segment["distance_km"] == 3.4
    assert segment["time_min"] == 45
    assert segment["cost"] == 2
    assert segment["options"][0]["mode"] == "公共交通"
    assert segment["options"][0]["detail"] == "步行 600m -> 地铁1号线 -> 步行 900m"
    assert segment["options"][1]["mode"] == "步行"
    assert segment["options"][1]["time_min"] == 38
    assert segment["options"][2]["mode"] == "打车/驾车"
    assert segment["options"][2]["cost"] == 18
    assert route_calls == [
        ("transit", "北京"),
        ("walking", None),
        ("driving", None),
    ]


def test_planning_agents_do_not_open_orm_sessions():
    # FoodAgent 使用 async_session_factory 补坐标/DB兜底（by design）
    for agent_class in (AttractionAgent, HotelAgent):
        source = inspect.getsource(agent_class)
        assert "async_session_factory" not in source
        assert "Repository" not in source


@pytest.mark.asyncio
async def test_attraction_agent_merges_weather_and_unique_candidate_metadata(monkeypatch, mock_llm):
    candidates = [
        {
            "id": "attr-1", "source": "amap", "source_poi_id": "B0ATTR",
            "name": "故宫博物院", "rating": 4.9, "price": 60,
            "latitude": 39.9163, "longitude": 116.3972,
            "address": "景山前街4号", "category": "博物馆", "tags": "历史;室内",
        },
        {"id": "attr-2", "name": "颐和园", "tags": "园林"},
        {"id": "attr-3", "name": "天坛公园", "tags": "公园"},
    ]

    async def fake_rag_search(*args, **kwargs):
        _ = args, kwargs
        return candidates

    captured = {}

    async def fake_llm_plan(candidates, destination, days, preferences, pace, weather_impact):
        _ = candidates, destination, days, preferences, pace
        captured["weather_impact"] = weather_impact
        return [{"day": 1, "attractions": [{"name": "故宫"}]}]

    monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag_search)
    agent = AttractionAgent(mock_llm)
    monkeypatch.setattr(agent, "_llm_plan", fake_llm_plan)
    weather = [{"day_of_trip": 1, "outdoor_suitability": 0.2}]

    result = await agent.run({
        "destination": "北京", "days": 1, "weather_impact": weather,
    })

    attraction = result["daily_plan"][0]["attractions"][0]
    assert captured["weather_impact"] == weather
    assert attraction["poi_id"] == "attr-1"
    assert attraction["source_poi_id"] == "B0ATTR"
    assert attraction["category"] == "博物馆"
    assert attraction["tags"] == "历史;室内"


def test_attraction_output_accepts_category_and_string_tags():
    from app.schemas.agent_outputs import AttractionOutput

    output = AttractionOutput.model_validate({
        "daily_plan": [{
            "day": 1,
            "attractions": [{"name": "故宫博物院", "category": "博物馆", "tags": "历史;室内"}],
        }],
    })

    attraction = output.daily_plan[0].attractions[0]
    assert attraction.category == "博物馆"
    assert attraction.tags == "历史;室内"


def test_food_candidate_metadata_survives_decision():
    meal_plan = [{"day": 1, "meals": [{"meal": "午餐", "restaurant": "蜀香居"}]}]
    food_module._attach_candidate_data(meal_plan, [{
        "poi_id": "restaurant-uuid",
        "source": "amap",
        "source_poi_id": "B0FOOD",
        "name": "蜀香居",
        "rating": 4.7,
        "avg_price": 88,
        "latitude": 30.67,
        "longitude": 104.06,
        "address": "春熙路1号",
    }])

    assert meal_plan[0]["meals"][0] == {
        "meal": "午餐",
        "restaurant": "蜀香居",
        "poi_id": "restaurant-uuid",
        "source": "amap",
        "source_poi_id": "B0FOOD",
        "rating": 4.7,
        "avg_price": 88,
        "latitude": 30.67,
        "longitude": 104.06,
        "address": "春熙路1号",
    }


@pytest.mark.asyncio
async def test_hotel_agent_merges_meituan_price_with_local_poi(monkeypatch, mock_llm):
    candidates = [{
        "id": "hotel-uuid",
        "source": "amap",
        "source_poi_id": "B0HOTEL",
        "name": "中心酒店",
        "latitude": 39.91,
        "longitude": 116.40,
        "address": "中心路1号",
        "rating": 4.6,
        "price_per_night": 480,
    }]

    async def fake_rag_search(*args, **kwargs):
        _ = args, kwargs
        return candidates

    async def fake_query(city, query):
        _ = city, query
        return {"success": True, "text": "hotel results"}

    monkeypatch.setattr(hotel_module, "rag_search", fake_rag_search)
    from app.services.third_party.meituan import meituan
    monkeypatch.setattr(type(meituan), "available", property(lambda self: True))
    monkeypatch.setattr(meituan, "query", fake_query)
    monkeypatch.setattr(
        "app.services.third_party.meituan_parser.parse_hotels",
        lambda text: [
            {"name": "中心酒店（春熙路店）", "price": 399, "rating": 4.8},
            {"name": "远方酒店", "price": 299, "rating": 4.4},
        ],
    )

    result = await HotelAgent(mock_llm).run({
        "destination": "北京", "days": 3, "budget_per_night": 500,
    })

    matched, unmatched = result["hotel_plan"]["recommendations"]
    assert matched["poi_id"] == "hotel-uuid"
    assert matched["source"] == "amap"
    assert matched["source_poi_id"] == "B0HOTEL"
    assert matched["price_source"] == "meituan"
    assert matched["coordinates_available"] is True
    assert unmatched["poi_id"] is None
    assert unmatched["coordinates_available"] is False


@pytest.mark.asyncio
async def test_hotel_agent_estimates_invalid_meituan_price(monkeypatch, mock_llm):
    async def fake_rag_search(*args, **kwargs):
        _ = args, kwargs
        return []

    async def fake_query(city, query):
        _ = city, query
        return {"success": True, "text": "hotel results"}

    class OfflineAmap:
        async def search_poi(self, **kwargs):
            _ = kwargs
            return []

    monkeypatch.setattr(hotel_module, "rag_search", fake_rag_search)
    monkeypatch.setattr("app.services.map.amap.AmapService", lambda: OfflineAmap())
    from app.services.third_party.meituan import meituan
    monkeypatch.setattr(type(meituan), "available", property(lambda self: True))
    monkeypatch.setattr(meituan, "query", fake_query)
    monkeypatch.setattr(
        "app.services.third_party.meituan_parser.parse_hotels",
        lambda text: [{"name": "测试酒店", "price": 1, "rating": 4.0}],
    )

    result = await HotelAgent(mock_llm).run({
        "destination": "北京", "days": 3, "budget_per_night": 500,
    })

    hotel = result["hotel_plan"]["recommendations"][0]
    assert hotel["raw_price"] == 1
    assert hotel["price_per_night"] == 500
    assert hotel["total"] == 1000
    assert hotel["price_verified"] is False
    assert hotel["estimated"] is True


def test_distinct_locations_without_coordinates_are_not_deduplicated():
    first = {"name": "地点甲", "latitude": None, "longitude": None}
    second = {"name": "地点乙", "latitude": None, "longitude": None}

    assert traffic_module._same(first, second) is False
    estimate = traffic_module._estimate(first, second, "transit")
    assert estimate["distance_km"] == 5.0
    assert estimate["time_min"] == 12
    assert traffic_module._estimate(first, second, "地铁")["cost"] == 15.0
    assert traffic_module._same({"name": ""}, {"name": ""}) is False


def test_weather_can_disable_walking_route():
    options = [
        {"route_type": "walking", "time_min": 10},
        {"route_type": "transit", "time_min": 20},
    ]

    selected = traffic_module._select_route_option(
        options, "步行", {"walking_viable": False},
    )

    assert selected["route_type"] == "transit"


def test_transit_parser_keeps_walking_and_bus_from_same_segment():
    route = {
        "transits": [{
            "duration": "1800",
            "distance": "6000",
            "walking_distance": "300",
            "segments": [{
                "walking": {
                    "distance": "300",
                    "duration": "240",
                    "steps": [{"instruction": "步行至地铁站", "road": "长安街"}],
                },
                "bus": {"buslines": [{
                    "name": "地铁1号线(苹果园--环球度假区)",
                    "type": "地铁线路",
                    "distance": "5700",
                    "duration": "1560",
                    "departure_stop": {"name": "天安门东"},
                    "arrival_stop": {"name": "国贸"},
                }]},
            }],
        }],
    }

    parsed = traffic_module._parse_transit(route)

    assert [segment["type"] for segment in parsed["plans"][0]["segments"]] == [
        "walking", "SUBWAY",
    ]
    assert parsed["detail"] == "步行 300m -> 地铁1号线(天安门东→国贸)"


def test_road_names_prefers_step_road_and_falls_back_to_district():
    assert traffic_module._road_names({
        "road": "长安街",
        "cities": [{"districts": [{"name": "东城区"}]}],
    }) == ["长安街"]
    assert traffic_module._road_names({
        "cities": [{"districts": [{"name": "东城区"}]}],
    }) == ["东城区"]


@pytest.mark.asyncio
async def test_decision_round1_deterministically_trims_overfull_day(mock_llm):
    attractions = [{"name": f"景点{i}"} for i in range(5)]

    result = await DecisionAgent(mock_llm).run_round1({
        "daily_plan": [{"day": 1, "attractions": attractions}],
        "meal_plan": [],
    })

    assert result["decision_needed"] is False
    assert result["auto_trimmed"] is True
    assert result["daily_plan"][0]["attractions"] == attractions[:4]


@pytest.mark.asyncio
async def test_decision_run_is_compatible_and_reports_finalized(mock_llm):
    attractions = [{"name": f"景点{i}"} for i in range(5)]

    result = await DecisionAgent(mock_llm).run({
        "daily_plan": [{"day": 1, "attractions": attractions}],
        "meal_plan": [],
    })

    assert result["stage"] == "finalized"
    assert result["auto_trimmed"] is True
    assert result["daily_plan"][0]["attractions"] == attractions[:4]


@pytest.mark.asyncio
async def test_decision_round1_preserves_boundary_and_matches_meals(mock_llm):
    day1 = [{"name": f"景点{i}"} for i in range(4)]
    day2 = [{"name": f"另一景点{i}"} for i in range(6)]
    meals = [
        {"day": 2, "meals": [{"meal": "晚餐", "restaurant": "餐厅乙"}]},
        {"day": 1, "meals": [{"meal": "午餐", "restaurant": "餐厅甲"}]},
    ]

    result = await DecisionAgent(mock_llm).run_round1({
        "daily_plan": [
            {"day": 1, "attractions": day1},
            {"day": 2, "attractions": day2},
        ],
        "meal_plan": meals,
    })

    assert result["auto_trimmed"] is True
    assert result["daily_plan"][0]["attractions"] == day1
    assert result["daily_plan"][0]["meals"] == meals[1]["meals"]
    assert result["daily_plan"][1]["attractions"] == day2[:4]
    assert result["daily_plan"][1]["meals"] == meals[0]["meals"]


@pytest.mark.asyncio
async def test_decision_round2_selects_highest_scored_hotel(
        mock_llm, monkeypatch):
    scored = [
        {"name": "酒店乙", "commute_score": 0.9},
        {"name": "酒店甲", "commute_score": 0.6},
    ]

    async def fake_evaluate(*args, **kwargs):
        _ = args, kwargs
        return scored

    monkeypatch.setattr(TrafficAgent, "evaluate_hotels", fake_evaluate)
    result = await DecisionAgent(mock_llm).run_round2({
        "hotel_plan": {"recommendations": list(reversed(scored))},
        "daily_plan": [{"day": 1, "attractions": [{"name": "景点"}]}],
        "destination": "北京",
    })

    hotel_plan = result["hotel_plan"]
    assert hotel_plan["selected"] == "酒店乙"
    assert hotel_plan["selected_hotel"] == scored[0]
    assert hotel_plan["selection_reason"] == "交通评分 0.9 最优"


@pytest.mark.asyncio
async def test_decision_round2_selects_first_hotel_without_daily_plan(mock_llm):
    first = {"name": "酒店甲"}
    result = await DecisionAgent(mock_llm).run_round2({
        "hotel_plan": {"recommendations": [first, {"name": "酒店乙"}]},
        "daily_plan": [],
    })

    hotel_plan = result["hotel_plan"]
    assert hotel_plan["selected"] == "酒店甲"
    assert hotel_plan["selected_hotel"] == first
    assert hotel_plan["selection_reason"] == "缺少可评估日程，按候选顺序选择"


@pytest.mark.asyncio
async def test_decision_round2_falls_back_when_scoring_fails(
        mock_llm, monkeypatch):
    async def fail_evaluate(*args, **kwargs):
        _ = args, kwargs
        raise RuntimeError("地图服务不可用")

    monkeypatch.setattr(TrafficAgent, "evaluate_hotels", fail_evaluate)
    first = {"name": "酒店甲"}
    result = await DecisionAgent(mock_llm).run_round2({
        "hotel_plan": {"recommendations": [first, {"name": "酒店乙"}]},
        "daily_plan": [{"day": 1, "attractions": [{"name": "景点"}]}],
    })

    hotel_plan = result["hotel_plan"]
    assert hotel_plan["selected"] == "酒店甲"
    assert hotel_plan["selected_hotel"] == first
    assert hotel_plan["selection_warning"] == "地图服务不可用"


@pytest.mark.asyncio
async def test_decision_round2_preserves_plan_without_candidates(mock_llm):
    original = {"recommendations": [], "source": "local"}

    result = await DecisionAgent(mock_llm).run_round2({"hotel_plan": original})

    assert result == {
        "hotel_plan": original,
        "decision_round2_done": True,
    }


@pytest.mark.asyncio
async def test_decision_nodes_pass_finalized_plans_forward(monkeypatch):
    from app.orchestrator import nodes as nodes_module

    class FakeDecisionAgent:
        def __init__(self, llm):
            _ = llm

        async def run_round1(self, input_data):
            return {
                "daily_plan": [{"day": 1, "attractions": input_data["daily_plan"][0]["attractions"][:4]}],
                "meal_plan": input_data["meal_plan"],
            }

        async def run_round2(self, input_data):
            selected = input_data["hotel_plan"]["recommendations"][1]
            return {"hotel_plan": {
                **input_data["hotel_plan"],
                "selected": selected["name"],
                "selected_hotel": selected,
            }}

    monkeypatch.setattr(nodes_module, "DecisionAgent", FakeDecisionAgent)
    attractions = [{"name": f"景点{i}"} for i in range(5)]
    hotels = [{"name": "酒店甲"}, {"name": "酒店乙"}]

    r1 = await nodes_module.node_decision_r1({
        "daily_plan": [{"day": 1, "attractions": attractions}],
        "meal_plan": [{"day": 1, "meals": []}],
    })
    r2 = await nodes_module.node_decision_r2({
        "daily_plan": r1["daily_plan"],
        "hotel_plan": {"recommendations": hotels},
        "destination": "北京",
    })

    assert r1["daily_plan"][0]["attractions"] == attractions[:4]
    assert r1["current_stage"] == "decision_r1"
    assert r2["hotel_plan"]["selected_hotel"] == hotels[1]
    assert r2["current_stage"] == "decision_r2"


@pytest.mark.asyncio
async def test_daily_traffic_uses_explicitly_selected_hotel():
    class OfflineAmap:
        async def route_planning(self, *args, **kwargs):
            _ = args, kwargs
            raise RuntimeError("offline")

    hotel_plan = {
        "selected": "酒店乙",
        "selected_hotel": {
            "name": "酒店乙", "latitude": 39.90, "longitude": 116.40,
        },
        "recommendations": [
            {"name": "酒店甲", "latitude": 39.80, "longitude": 116.30},
            {"name": "酒店乙", "latitude": 39.90, "longitude": 116.40},
        ],
    }
    daily, _ = await traffic_module._plan_daily(
        OfflineAmap(),
        [{"day": 1, "attractions": [
            {"name": "景点", "latitude": 39.91, "longitude": 116.41},
        ]}],
        [],
        hotel_plan,
        {},
        "transit",
    )

    segments = daily[0]["segments"]
    assert segments[0]["from"] == "酒店乙"
    assert segments[-1]["to"] == "酒店乙"
    assert all("酒店甲" not in (segment["from"], segment["to"]) for segment in segments)


@pytest.mark.asyncio
async def test_big_traffic_returns_to_destination_hub(monkeypatch):
    hubs = {
        "武汉": {"airport": None, "station": {"name": "武汉站", "lat": 30.61, "lng": 114.42, "type": "station"}},
        "北京": {"airport": None, "station": {"name": "北京站", "lat": 39.90, "lng": 116.43, "type": "station"}},
    }

    async def fake_find_hubs(amap, city):
        _ = amap
        return hubs[city]

    monkeypatch.setattr(traffic_module, "_find_hubs", fake_find_hubs)
    from app.services.third_party.railway12306 import railway
    from app.services.third_party.meituan import meituan
    monkeypatch.setattr(railway, "query_all_trains", lambda *args, **kwargs: [])
    monkeypatch.setattr(type(meituan), "available", property(lambda self: False))

    result = await traffic_module._big_traffic(
        "武汉",
        "北京",
        {},
        object(),
        days=3,
        start_date="2099-08-01",
        end_date="2099-08-03",
    )

    assert result["origin_hub"]["name"] == "武汉站"
    assert result["arrival_hub"]["name"] == "北京站"
    assert result["departure_hub"]["name"] == "北京站"


@pytest.mark.asyncio
async def test_big_traffic_hub_route_uses_first_day_weather_and_city(monkeypatch):
    route_calls = []

    async def fake_find_hubs(amap, city):
        _ = amap
        return {
            "airport": None,
            "station": {
                "name": f"{city}站",
                "lat": 39.9,
                "lng": 116.4,
                "type": "station",
            },
        }

    class FakeAmap:
        async def route_planning(
            self,
            origin,
            destination,
            route_type="transit",
            city=None,
        ):
            _ = origin, destination
            route_calls.append((route_type, city))
            if route_type == "transit":
                return {
                    "transits": [{
                        "duration": "600",
                        "cost": "2",
                        "distance": "5000",
                        "segments": [],
                    }],
                }
            return {}

    monkeypatch.setattr(traffic_module, "_find_hubs", fake_find_hubs)
    from app.services.third_party.railway12306 import railway
    from app.services.third_party.meituan import meituan
    monkeypatch.setattr(railway, "query_all_trains", lambda *args, **kwargs: [])
    monkeypatch.setattr(type(meituan), "available", property(lambda self: False))

    result = await traffic_module._big_traffic(
        "武汉",
        "北京",
        {
            "selected_hotel": {
                "name": "北京饭店",
                "latitude": 39.91,
                "longitude": 116.41,
            },
        },
        FakeAmap(),
        days=3,
        start_date="2099-08-01",
        end_date="2099-08-03",
        first_day_weather={
            "traffic_speed_factor": 0.5,
            "walking_viable": False,
            "preferred_mode": "transit",
        },
    )

    assert result["hub_to_hotel"]["time_min"] == 20
    assert result["hub_to_hotel"]["cost"] == 2
    assert route_calls == [
        ("transit", "北京"),
        ("walking", None),
        ("driving", None),
    ]


@pytest.mark.asyncio
async def test_node_budget_passes_detail_agent_output(monkeypatch):
    from app.orchestrator import nodes as nodes_module

    captured = {}

    class FakeBudgetAgent:
        def __init__(self, llm):
            _ = llm

        async def run(self, input_data):
            captured.update(input_data)
            return {
                "final_plan": {
                    "attraction_details": input_data["attraction_details"],
                    "food_details": input_data["food_details"],
                },
                "should_retry": False,
                "adjusted_params": {},
                "retry_count": 0,
            }

    monkeypatch.setattr(nodes_module, "BudgetAgent", FakeBudgetAgent)
    attraction_details = [{"name": "故宫博物院", "tips": "提前预约"}]
    food_details = [{"name": "蜀香居", "signature": "水煮鱼"}]

    result = await nodes_module.node_budget({
        "destination": "北京",
        "days": 1,
        "daily_plan": [],
        "meal_plan": [],
        "hotel_plan": {
            "selected": "酒店乙",
            "recommendations": [
                {"name": "酒店甲", "total": 900},
                {"name": "酒店乙", "total": 600},
            ],
        },
        "traffic": {},
        "attraction_details": attraction_details,
        "food_details": food_details,
    })

    assert captured["attraction_details"] == attraction_details
    assert captured["food_details"] == food_details
    assert captured["expenses"]["hotels"] == 600
    final_plan = result["final_plan"]
    assert final_plan["attraction_details"] == attraction_details
    assert final_plan["food_details"] == food_details
    assert final_plan["weather_forecast"] == []
    assert final_plan["weather_impact"] == []
    assert final_plan["weather_status"] == "fallback"


def test_railway_parse_adds_station_names():
    railway = Railway12306()
    railway._stations = {
        "武汉": "WHN",
        "北京西": "BXP",
        "广州南": "IZQ",
        "北京": "BJP",
    }
    fields = [""] * 36
    fields[2] = "240000G66B0"
    fields[3] = "G66"
    fields[4] = "IZQ"
    fields[5] = "BJP"
    fields[6] = "WHN"
    fields[7] = "BXP"
    fields[8] = "07:00"
    fields[9] = "12:00"
    fields[10] = "05:00"
    fields[13] = "20260710"
    fields[16] = "03"
    fields[17] = "09"
    fields[30] = "有"
    fields[35] = "OM"
    raw = json.dumps({"httpstatus": 200, "data": {"result": ["|".join(fields)]}})

    train = railway._parse(raw)[0]

    assert train["fromStation"] == "WHN"
    assert train["toStation"] == "BXP"
    assert train["fromStationName"] == "武汉"
    assert train["toStationName"] == "北京西"
    assert train["startStationName"] == "广州南"
    assert train["endStationName"] == "北京"


def test_railway_price_url_uses_left_ticket_endpoint():
    assert PRICE_URL == "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"


def test_railway_price_uses_station_numbers(monkeypatch):
    requested = {}

    class FakeResponse:
        def json(self):
            return {"httpstatus": 200, "data": {"O": "¥152.5"}}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            _ = args

        def get(self, url, headers=None):
            _ = headers
            if url.startswith(PRICE_URL):
                requested["url"] = url
            return FakeResponse()

    railway = Railway12306()
    monkeypatch.setattr(railway, "_client", lambda: FakeClient())

    prices = railway.query_price("240000G66B0", "03", "09", "2026-07-11", "OM")

    assert prices == {"二等座": "152.5"}
    assert "from_station_no=03" in requested["url"]
    assert "to_station_no=09" in requested["url"]
    assert "seat_types=OM" in requested["url"]
    assert "WHN" not in requested["url"]


@pytest.mark.asyncio
async def test_big_traffic_merges_prices_and_keeps_failed_train(monkeypatch):
    async def fake_find_hubs(amap, city):
        _ = amap
        return {
            "airport": None,
            "station": {"name": f"{city}站", "lat": 30.0, "lng": 110.0, "type": "station"},
        }

    trains = [
        {
            "trainNo": "train-1", "fromStationNo": "03", "toStationNo": "09",
            "seatTypes": "OM",
        },
        {
            "trainNo": "train-2", "fromStationNo": "04", "toStationNo": "10",
            "seatTypes": "O",
        },
    ]
    price_calls = []

    def fake_query_price(train_no, from_station_no, to_station_no, date, seat_types):
        price_calls.append((train_no, from_station_no, to_station_no, date, seat_types))
        if train_no == "train-2":
            raise RuntimeError("12306 unavailable")
        return {"二等座": "152.5"}

    monkeypatch.setattr(traffic_module, "_find_hubs", fake_find_hubs)
    from app.services.third_party.railway12306 import railway
    from app.services.third_party.meituan import meituan
    monkeypatch.setattr(railway, "query_all_trains", lambda *args, **kwargs: trains)
    monkeypatch.setattr(railway, "query_price", fake_query_price)
    monkeypatch.setattr(type(meituan), "available", property(lambda self: False))

    result = await traffic_module._big_traffic(
        "武汉",
        "北京",
        {},
        object(),
        days=3,
        start_date="2099-08-01",
        end_date="2099-08-03",
    )

    assert result["trains"] == [
        {**trains[0], "prices": {"二等座": "152.5"}},
        {**trains[1], "prices": {}},
    ]
    assert [(call[0], call[1], call[2], call[4]) for call in price_calls] == [
        ("train-1", "03", "09", "OM"),
        ("train-2", "04", "10", "O"),
        ("train-1", "03", "09", "OM"),
        ("train-2", "04", "10", "O"),
    ]
    assert [call[3] for call in price_calls] == [
        "2099-08-01",
        "2099-08-01",
        "2099-08-03",
        "2099-08-03",
    ]


def test_pipeline_train_fare_pairs_price_with_availability():
    train = {
        "prices": {"硬座": "152.5", "硬卧": "261.5", "无座": "152.5"},
        "hardSeat": "无票",
        "hardSleeper": "无票",
        "noSeat": "有票",
        "secondClass": "--",
    }

    assert _train_fare(train) == "硬卧 ¥261.5 无票 / 硬座 ¥152.5 无票 / 无座 ¥152.5 有票"


def test_pipeline_traffic_option_text():
    assert _traffic_option_text({
        "route_type": "transit",
        "detail": "步行 600m -> 地铁1号线 -> 步行 900m",
        "time_min": 45,
        "cost": 2,
    }) == "步行 600m -> 地铁1号线 -> 步行 900m"
    assert _traffic_option_text({
        "route_type": "walking",
        "time_min": 38,
        "cost": 0,
    }) == "38min ¥0"
    assert _traffic_option_text({
        "route_type": "driving",
        "time_min": 18,
        "cost": 18,
        "estimated_cost": True,
    }) == "18min 约¥18"


@pytest.mark.asyncio
async def test_route_optimizer_agent(mock_llm):
    agent = RouteOptimizerAgent(mock_llm)
    result = await agent.run({
        "daily_itinerary": [],
        "preferred_transport": "地铁",
    })
    assert "optimized_itinerary" in result


@pytest.mark.asyncio
async def test_souvenir_agent(mock_llm):
    agent = SouvenirAgent(mock_llm)
    result = await agent.run({
        "destination": "北京",
        "preferences": ["特产", "文创"],
        "remaining_budget": 500,
    })
    assert "souvenirs" in result
