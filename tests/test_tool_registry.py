"""测试 app/agents/tools/tool_registry.py — 工具注册中心"""

import pytest
from app.agents.tools.tool_registry import (
    register,
    get_tool_defs,
    get_handler,
    _registry,
)


# 每个测试前清空 registry
@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


class TestRegister:
    def test_register_adds_to_registry(self):
        async def fake_handler(**kwargs):
            return {"ok": True}

        register("test_tool", "A test tool", {"type": "object", "properties": {}}, fake_handler)
        assert "test_tool" in _registry
        assert _registry["test_tool"]["name"] == "test_tool"
        assert _registry["test_tool"]["description"] == "A test tool"

    def test_handler_is_stored(self):
        async def my_handler(city: str):
            return {"city": city}

        register("my_tool", "desc", {"type": "object"}, my_handler)
        stored = get_handler("my_tool")
        assert stored is my_handler


class TestGetToolDefs:
    def test_returns_openai_function_format(self):
        async def h(**kwargs):
            pass

        register("search", "search tool", {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        }, h)

        defs = get_tool_defs()
        assert len(defs) == 1
        assert defs[0]["type"] == "function"
        assert defs[0]["function"]["name"] == "search"
        assert defs[0]["function"]["parameters"]["required"] == ["city"]

    def test_empty_registry_returns_empty_list(self):
        assert get_tool_defs() == []

    def test_multiple_tools(self):
        async def h(**kwargs):
            pass

        register("t1", "d1", {"type": "object"}, h)
        register("t2", "d2", {"type": "object"}, h)
        assert len(get_tool_defs()) == 2


class TestGetHandler:
    def test_known_tool_returns_handler(self):
        async def h(**kwargs):
            pass

        register("known", "desc", {}, h)
        assert get_handler("known") is h

    def test_unknown_tool_returns_none(self):
        assert get_handler("nonexistent") is None


# ═══════════════════════════════════════════════════════
# Handler 函数（mock 外部服务）
# ═══════════════════════════════════════════════════════

class TestSearchAttractions:
    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, monkeypatch):
        async def fake_rag_search(collection, query, where=None, final_k=20, **kwargs):
            return [
                {"name": "故宫", "rating": 4.8, "price": 60, "tags": "历史", "address": "东城区", "relevance": 0.9, "rerank_score": 0.95},
            ]

        monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag_search)

        from app.agents.tools.tool_registry import _search_attractions
        result = await _search_attractions("北京", "历史")
        assert result["count"] == 1
        assert result["attractions"][0]["name"] == "故宫"
        assert result["attractions"][0]["rerank_score"] == 0.95

    @pytest.mark.asyncio
    async def test_handles_rag_exception(self, monkeypatch):
        async def failing_rag(**kwargs):
            raise RuntimeError("RAG down")

        monkeypatch.setattr("app.services.vector.rag.rag_search", failing_rag)

        from app.agents.tools.tool_registry import _search_attractions
        result = await _search_attractions("北京")
        assert result["count"] == 0
        assert result["attractions"] == []


class TestSearchRestaurants:
    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, monkeypatch):
        async def fake_rag_search(collection, query, where=None, final_k=20, **kwargs):
            return [
                {"name": "全聚德", "cuisine": "京菜", "rating": 4.5, "avg_price": 150, "tags": "烤鸭", "relevance": 0.85},
            ]

        monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag_search)

        from app.agents.tools.tool_registry import _search_restaurants
        result = await _search_restaurants("北京", cuisine="烤鸭", budget=200)
        assert result["count"] == 1
        assert result["restaurants"][0]["name"] == "全聚德"


class TestGetWeather:
    @pytest.mark.asyncio
    async def test_handles_service_exception(self, monkeypatch):
        class FakeQWeather:
            async def get_current_weather(self, city):
                raise RuntimeError("API error")

        monkeypatch.setattr("app.services.weather.qweather.qweather_service", FakeQWeather())

        from app.agents.tools.tool_registry import _get_weather
        result = await _get_weather("北京")
        assert "error" in result


class TestGetRoute:
    @pytest.mark.asyncio
    async def test_returns_route(self, monkeypatch):
        class FakeAmap:
            async def route_planning(self, origin, destination, mode):
                return {"distance": 1000, "duration": 600}

        monkeypatch.setattr("app.services.map.amap.AmapService", lambda api_key="": FakeAmap())

        from app.agents.tools.tool_registry import _get_route
        result = await _get_route(39.9, 116.4, 39.91, 116.41)
        assert "route" in result

    @pytest.mark.asyncio
    async def test_handles_exception(self, monkeypatch):
        class FakeAmap:
            async def route_planning(self, origin, destination, mode):
                raise RuntimeError("network error")

        monkeypatch.setattr("app.services.map.amap.AmapService", lambda api_key="": FakeAmap())

        from app.agents.tools.tool_registry import _get_route
        result = await _get_route(1, 2, 3, 4)
        assert "error" in result


class TestMeituanQuery:
    @pytest.mark.asyncio
    async def test_successful_query(self, monkeypatch):
        class FakeMeituan:
            async def query(self, city, query):
                return {"success": True, "text": "找到3家酒店"}

        monkeypatch.setattr("app.services.third_party.meituan.meituan", FakeMeituan())

        from app.agents.tools.tool_registry import _meituan_query
        result = await _meituan_query("北京", "故宫附近酒店")
        assert result["text"] == "找到3家酒店"
        assert result["source"] == "meituan"

    @pytest.mark.asyncio
    async def test_failed_query(self, monkeypatch):
        class FakeMeituan:
            async def query(self, city, query):
                return {"success": False, "error": "timeout"}

        monkeypatch.setattr("app.services.third_party.meituan.meituan", FakeMeituan())

        from app.agents.tools.tool_registry import _meituan_query
        result = await _meituan_query("北京", "测试")
        assert "error" in result


# ═══════════════════════════════════════════════════════
# Railway 处理器（mock railway 模块）
# ═══════════════════════════════════════════════════════

class TestRailwayTrains:
    @pytest.mark.asyncio
    async def test_returns_trains(self, monkeypatch):
        class FakeRailway:
            def query_all_trains(self, from_city, to_city, date=""):
                return [{"trainCode": "G1", "departureTime": "08:00", "arrivalTime": "12:30"}]

        monkeypatch.setattr("app.services.third_party.railway12306.railway", FakeRailway())

        from app.agents.tools.tool_registry import _railway_trains
        result = await _railway_trains("北京", "上海")
        assert result["count"] == 1
        assert result["trains"][0]["trainCode"] == "G1"
        assert result["source"] == "12306"


class TestRailwayPrice:
    @pytest.mark.asyncio
    async def test_returns_prices(self, monkeypatch):
        class FakeRailway:
            def query_all_trains(self, from_city, to_city, date=""):
                return [{"trainNo": "G1", "fromStationNo": "BJP", "toStationNo": "SHH", "seatTypes": ""}]

            def query_price(self, train_no, from_station_no, to_station_no, date="", seat_types=""):
                return [{"seatType": "二等座", "price": 553}]

        monkeypatch.setattr("app.services.third_party.railway12306.railway", FakeRailway())

        from app.agents.tools.tool_registry import _railway_price
        result = await _railway_price("G1", "北京", "上海")
        assert result["prices"][0]["price"] == 553
        assert result["source"] == "12306"


class TestRailwayStops:
    @pytest.mark.asyncio
    async def test_returns_stops(self, monkeypatch):
        class FakeRailway:
            def query_stops(self, train_no, from_city, to_city, date=""):
                return [{"stationName": "南京南", "arrivalTime": "10:00"}]

        monkeypatch.setattr("app.services.third_party.railway12306.railway", FakeRailway())

        from app.agents.tools.tool_registry import _railway_stops
        result = await _railway_stops("G1", "北京", "上海")
        assert result["count"] == 1
        assert result["source"] == "12306"
