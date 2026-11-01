"""测试 app/agents/detail_agent.py — DetailAgent"""

import pytest
from tests.test_llm import MockLLM
from app.agents.detail_agent import DetailAgent, _parse_attr_text, _parse_food_text


@pytest.fixture
def mock_llm():
    return MockLLM(api_key="test", base_url="http://test", model="test")


@pytest.fixture
def agent(mock_llm):
    return DetailAgent(mock_llm)


# ═══════════════════════════════════════════════════════
# 挑选函数（纯同步，无外部依赖）
# ═══════════════════════════════════════════════════════

class TestPickAttractions:
    def test_picks_top_by_rating(self, agent):
        daily_plan = [
            {"day": 1, "attractions": [
                {"name": "景点A", "rating": 4.5},
                {"name": "景点B", "rating": 4.8},
                {"name": "景点C", "rating": 4.2},
                {"name": "景点D", "rating": 4.9},
                {"name": "景点E", "rating": 4.6},
            ]},
            {"day": 2, "attractions": [
                {"name": "景点F", "rating": 4.7},
            ]},
        ]
        result = agent._pick_attractions(daily_plan)
        assert len(result) == 3  # MAX_ATTR_DETAIL
        names = [a["name"] for a in result]
        assert names == ["景点D", "景点B", "景点F"]


    def test_picks_respects_max_limit(self, agent):
        daily_plan = [
            {"day": 1, "attractions": [{"name": f"景点{i}", "rating": 4.5} for i in range(10)]},
        ]
        result = agent._pick_attractions(daily_plan)
        assert len(result) == DetailAgent.MAX_ATTR_DETAIL


    def test_empty_list_returns_empty(self, agent):
        assert agent._pick_attractions([]) == []


    def test_missing_rating_treated_as_zero(self, agent):
        daily_plan = [
            {"day": 1, "attractions": [
                {"name": "无评分景点"},
            ]},
        ]
        result = agent._pick_attractions(daily_plan)
        assert len(result) == 1
        assert result[0]["name"] == "无评分景点"


    def test_day_field_preserved(self, agent):
        daily_plan = [
            {"day": 3, "attractions": [{"name": "晚到的景点", "rating": 5.0}]},
        ]
        result = agent._pick_attractions(daily_plan)
        assert result[0]["day"] == 3


class TestPickRestaurants:
    def test_picks_top_by_price(self, agent):
        meal_plan = [
            {"day": 1, "meals": [
                {"restaurant": "餐厅A", "avg_price": 80},
                {"restaurant": "餐厅B", "avg_price": 200},
                {"restaurant": "餐厅C", "avg_price": 50},
            ]},
            {"day": 2, "meals": [
                {"restaurant": "餐厅D", "avg_price": 150},
                {"restaurant": "餐厅E", "avg_price": 300},
            ]},
        ]
        result = agent._pick_restaurants(meal_plan)
        assert len(result) == DetailAgent.MAX_FOOD_DETAIL
        names = [r["restaurant"] for r in result]
        assert names == ["餐厅E", "餐厅B", "餐厅D"]


    def test_empty_list_returns_empty(self, agent):
        assert agent._pick_restaurants([]) == []


    def test_avg_price_none_treated_as_zero(self, agent):
        meal_plan = [
            {"day": 1, "meals": [{"restaurant": "无名", "avg_price": None}]},
        ]
        result = agent._pick_restaurants(meal_plan)
        assert result[0]["restaurant"] == "无名"


# ═══════════════════════════════════════════════════════
# 模块级解析函数（纯同步，无外部依赖）
# ═══════════════════════════════════════════════════════

class TestParseAttrText:
    def test_parses_tips_and_spots(self):
        text = """## 故宫攻略
注意：需要提前预约门票
必去：太和殿、乾清宫
推荐：珍宝馆
开放时间：8:30-17:00
亮点：红墙黄瓦
建议：穿舒适的鞋子"""
        result = _parse_attr_text(text)
        assert result is not None
        assert "tips" in result
        assert any("预约" in t for t in result["tips"])
        assert "famous_spots" in result
        assert any("太和殿" in s for s in result["famous_spots"])

    def test_parses_tips_only(self):
        text = "注意：只能现场买票\n提示：避开周末\n开放：9:00-18:00"
        result = _parse_attr_text(text)
        assert result is not None
        assert "tips" in result
        assert "famous_spots" not in result
        assert len(result["tips"]) <= 5

    def test_parses_spots_only(self):
        text = "必去：外滩\n打卡：东方明珠\n推荐：田子坊"
        result = _parse_attr_text(text)
        assert result is not None
        assert "famous_spots" in result
        assert "tips" not in result

    def test_empty_text_returns_none(self):
        assert _parse_attr_text("") is None

    def test_no_labels_returns_none(self):
        text = "这是一段没有明显关键词的描述文本。" * 10
        assert _parse_attr_text(text) is None

    def test_skips_heading_lines(self):
        text = "# 标题\n---\n注意：重要提示"
        result = _parse_attr_text(text)
        assert result is not None
        assert "tips" in result

    def test_filters_meituan_assistant_copy_from_attraction_details(self):
        text = (
            "国家植物园是北京的4A级宝藏景区，集科研、科普和游览于一体。"
            "小团帮你整理了著名景点和游玩注意事项，快来看看吧～🌿；"
            "时间与门票：北园开放时间 06:00-21:00，建议提前购票入园\n"
            "必打卡：喷雾水杉林仙境、卧佛寺古刹、樱桃沟"
        )

        result = _parse_attr_text(text)

        assert result == {
            "tips": ["北园开放时间 06:00-21:00，建议提前购票入园"],
            "famous_spots": ["喷雾水杉林仙境、卧佛寺古刹、樱桃沟"],
        }
        assert "小团" not in str(result)

    def test_parses_bullets_under_explicit_section_heading(self):
        text = "## 注意事项\n提前预约门票\n## 必打卡\n- 太和殿、乾清宫"

        result = _parse_attr_text(text)

        assert result == {
            "tips": ["提前预约门票"],
            "famous_spots": ["太和殿、乾清宫"],
        }

    def test_deduplicates_values(self):
        text = "注意：提前预约\n提示：提前预约\n必去：太和殿\n必打卡：太和殿"

        result = _parse_attr_text(text)

        assert result == {"tips": ["提前预约"], "famous_spots": ["太和殿"]}


class TestParseFoodText:
    def test_parses_signature_dishes(self):
        text = "招牌：北京烤鸭\n推荐菜：宫保鸡丁\n必点：麻婆豆腐"
        result = _parse_food_text(text)
        assert result is not None
        assert "signature_dishes" in result
        assert any("烤鸭" in d for d in result["signature_dishes"])

    def test_parses_user_feedback(self):
        text = "好评：环境优雅\n口碑：服务一流\n评分：4.8"
        result = _parse_food_text(text)
        assert result is not None
        assert "user_feedback" in result
        assert len(result["user_feedback"]) <= 3

    def test_empty_text_returns_none(self):
        assert _parse_food_text("") is None

    def test_no_labels_returns_none(self):
        text = "一家普通的餐厅描述。" * 20
        assert _parse_food_text(text) is None

    def test_rejects_no_result_response_for_wrong_city_restaurant(self):
        text = (
            "小团帮你查了一下淄博的“有礼有面”，目前暂时没有查询到这家店的"
            "招牌菜和详细用户评价哦。不过别担心，小团为你找到了其他信息。"
        )

        assert _parse_food_text(text) is None

    def test_extracts_dish_after_assistant_preamble(self):
        text = (
            "你好呀！想了解山海食堂的招牌菜和用户评价是吗？"
            "小团这就为你奉上最全的探店信息！😋、"
            "招牌必点：熔岩饭和芝士豆腐是店里的招牌，很多食客都强烈推荐"
        )

        result = _parse_food_text(text)

        assert result == {"signature_dishes": ["熔岩饭和芝士豆腐"]}
        assert "小团" not in str(result)

    def test_rejects_unstructured_assistant_copy(self):
        text = "小团帮你整理了这家店的特色，快来看看吧。"

        assert _parse_food_text(text) is None


# ═══════════════════════════════════════════════════════
# run() 集成（mock 外部服务）
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_run_with_empty_inputs(agent):
    result = await agent.run({"daily_plan": [], "meal_plan": [], "destination": ""})
    assert "attraction_details" in result
    assert "food_details" in result
    assert result["attraction_details"] == []
    assert result["food_details"] == []


@pytest.mark.asyncio
async def test_run_calls_fetch_for_picks(agent, monkeypatch):
    canned_attr = [{"name": "故宫", "day": 1, "tips": ["提前预约"]}]
    canned_food = [{"name": "全聚德", "day": 1, "signature_dishes": ["烤鸭"]}]

    async def fake_fetch_attr(self, picks, city):
        return canned_attr

    async def fake_fetch_food(self, picks, city):
        return canned_food

    monkeypatch.setattr(DetailAgent, "_fetch_attr_details", fake_fetch_attr)
    monkeypatch.setattr(DetailAgent, "_fetch_food_details", fake_fetch_food)

    daily_plan = [{"day": 1, "attractions": [{"name": "故宫", "rating": 4.5}]}]
    meal_plan = [{"day": 1, "meals": [{"restaurant": "全聚德", "avg_price": 200}]}]

    result = await agent.run({
        "daily_plan": daily_plan,
        "meal_plan": meal_plan,
        "destination": "北京",
    })

    assert result["attraction_details"] == canned_attr
    assert result["food_details"] == canned_food


@pytest.mark.asyncio
async def test_fetch_one_attr_empty_name_returns_none(agent):
    result = await agent._fetch_one_attr({"name": ""}, "北京")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_one_food_empty_name_returns_none(agent):
    result = await agent._fetch_one_food({"restaurant": ""}, "北京")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_one_attr_meituan_fallback_to_amap(agent, monkeypatch):
    """当美团不可用时回退到高德 POI 搜索"""
    monkeypatch.setattr(
        "app.services.third_party.meituan.meituan", type("FakeMeituan", (), {"available": False})(), raising=False
    )

    class FakeAmapService:
        async def search_poi(self, **kwargs):
            return [{"business_area": "东城区", "address": "北京市东城区景山前街4号"}]

    monkeypatch.setattr(
        "app.services.map.amap.AmapService", lambda api_key="": FakeAmapService()
    )

    result = await agent._fetch_one_attr({"name": "故宫", "rating": 4.8, "day": 1}, "北京")
    assert result is not None
    assert result["name"] == "故宫"
    assert "tips" in result or "address" in result


@pytest.mark.asyncio
async def test_fetch_one_attr_meituan_success(agent, monkeypatch):
    """美团成功返回数据"""
    class FakeMeituan:
        available = True
        async def query(self, city, q):
            return {"success": True, "text": "注意：提前预约\n必去：太和殿"}

    monkeypatch.setattr(
        "app.services.third_party.meituan.meituan", FakeMeituan()
    )

    result = await agent._fetch_one_attr({"name": "故宫", "rating": 4.8, "day": 1}, "北京")
    assert result is not None
    assert "tips" in result
    assert len(result["tips"]) > 0


@pytest.mark.asyncio
async def test_fetch_one_food_meituan_success(agent, monkeypatch):
    """美团成功返回餐厅数据"""
    class FakeMeituan:
        available = True
        async def query(self, city, q):
            return {"success": True, "text": "招牌：烤鸭\n推荐菜：宫保鸡丁"}

    monkeypatch.setattr(
        "app.services.third_party.meituan.meituan", FakeMeituan()
    )

    result = await agent._fetch_one_food({"restaurant": "全聚德", "day": 1, "avg_price": 200}, "北京")
    assert result is not None
    assert "signature_dishes" in result


@pytest.mark.asyncio
async def test_fetch_one_food_no_signature_returns_none(agent, monkeypatch):
    """美团返回不含结构化详情时不生成空详情。"""
    class FakeMeituan:
        available = True
        async def query(self, city, q):
            return {"success": True, "text": "普通描述"}

    monkeypatch.setattr(
        "app.services.third_party.meituan.meituan", FakeMeituan()
    )

    result = await agent._fetch_one_food({"restaurant": "某餐厅"}, "北京")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_one_attr_without_meituan_or_amap_content_returns_none(
    agent, monkeypatch,
):
    class FakeMeituan:
        available = True

        async def query(self, city, q):
            return {"success": True, "text": "普通描述"}

    class FakeAmapService:
        async def search_poi(self, **kwargs):
            return []

    monkeypatch.setattr("app.services.third_party.meituan.meituan", FakeMeituan())
    monkeypatch.setattr("app.services.map.amap.AmapService", lambda: FakeAmapService())

    result = await agent._fetch_one_attr({"name": "某景点", "rating": 4.8}, "北京")

    assert result is None
