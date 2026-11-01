"""测试 app/agents/traffic_agent.py — 已验证签名的同步函数"""

import pytest
from app.agents.traffic_agent import (
    _same, _dedupe, _selected_hotel,
    _day_meals, _ai, _af, _coordinates, _coord,
    _apply_weather_speed_factor, _route_type, _select_route_option,
)


class TestSame:
    def test_same_name(self):
        assert _same({"name": "故宫"}, {"name": "故宫"}) is True

    def test_different(self):
        assert _same({"name": "A"}, {"name": "B"}) is False

    def test_nearby_coordinates(self):
        assert _same({"name": "a", "latitude": 39.9, "longitude": 116.4},
                     {"name": "b", "latitude": 39.90005, "longitude": 116.40005}) is True

    def test_no_coordinates_different_names(self):
        assert _same({"name": "A"}, {"name": "B"}) is False


class TestDedupe:
    def test_deduplicates(self):
        result = _dedupe([{"name": "X"}, {"name": "X"}, {"name": "Y"}])
        assert len(result) == 2

    def test_keeps_unique(self):
        result = _dedupe([{"name": "A"}, {"name": "B"}, {"name": "C"}])
        assert len(result) == 3


class TestSelectedHotel:
    def test_from_dict(self):
        result = _selected_hotel({"selected_hotel": {"name": "北京饭店"}})
        assert result["name"] == "北京饭店"

    def test_fallback(self):
        result = _selected_hotel({"recommendations": [{"name": "唯一酒店"}]})
        assert result["name"] == "唯一酒店"

    def test_empty(self):
        assert _selected_hotel({}) == {}


class TestDayMeals:
    def test_filters(self):
        mp = [{"day": 1, "meals": [{"meal": "午餐"}]}, {"day": 2, "meals": [{"meal": "晚餐"}]}]
        assert _day_meals(mp, 1) == [{"meal": "午餐"}]
        assert _day_meals(mp, 99) == []


class TestAiAf:
    def test_ai_int(self):
        assert _ai(5) == 5

    def test_ai_default(self):
        assert _ai(None, 10) == 10

    def test_af_float(self):
        assert _af(1.5) == 1.5

    def test_af_default(self):
        assert _af(None, 2.0) == 2.0


class TestCoordinates:
    def test_valid(self):
        lat, lng = _coordinates({"latitude": 39.9, "longitude": 116.4})
        assert lat == 39.9
        assert lng == 116.4


class TestCoord:
    def test_float_val(self):
        assert _coord({"latitude": 39.9, "longitude": 116.4}) == "116.4,39.9"
        assert _coord({}) is None


class TestWeatherAwareRouteSelection:
    def test_normal_weather_keeps_user_walking_preference(self):
        opts = [
            {"route_type": "transit", "time_min": 20},
            {"route_type": "walking", "time_min": 12},
        ]
        result = _select_route_option(
            opts,
            "walking",
            {"walking_viable": True, "preferred_mode": "walking"},
        )
        assert result["route_type"] == "walking"

    def test_bad_weather_filters_walking_and_prefers_transit(self):
        opts = [
            {"route_type": "walking", "time_min": 12},
            {"route_type": "transit", "time_min": 20},
            {"route_type": "driving", "time_min": 15},
        ]
        result = _select_route_option(
            opts,
            "walking",
            {"walking_viable": False, "preferred_mode": "transit"},
        )
        assert result["route_type"] == "transit"

    def test_weather_speed_factor_changes_only_duration(self):
        options = [{
            "route_type": "transit",
            "time_min": 21,
            "distance_km": 4.2,
            "cost": 3,
        }]

        result = _apply_weather_speed_factor(
            options,
            {"traffic_speed_factor": 0.7},
        )

        assert result[0]["time_min"] == 30
        assert result[0]["distance_km"] == 4.2
        assert result[0]["cost"] == 3

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Walking", "walking"),
            ("公交", "transit"),
            ("SUBWAY", "transit"),
            ("Taxi", "driving"),
        ],
    )
    def test_transport_aliases_are_normalized(self, value, expected):
        assert _route_type(value) == expected
