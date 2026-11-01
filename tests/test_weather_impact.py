"""测试 app/services/weather/impact.py"""

import pytest
from app.services.weather.impact import (
    calculate_weather_impact,
    build_neutral_impacts,
    _classify_severity,
    _weather_factor,
    _temp_factor,
    _wind_factor,
    _compute_outdoor_suitability,
    _traffic_speed_factor,
    _is_walking_viable,
    _compute_preferred_mode,
    _classify_heat_risk,
    _generate_advice,
    _safe_float,
)


class TestSafeFloat:
    def test_normal_number(self):
        assert _safe_float("32") == 32.0

    def test_range_takes_max(self):
        assert _safe_float("1-3") == 3.0

    def test_arrow_prefix(self):
        assert _safe_float("<3") == 3.0

    def test_none_returns_default(self):
        assert _safe_float(None, default=22.0) == 22.0

    def test_empty_string(self):
        assert _safe_float("") == 0.0

    def test_invalid_string(self):
        assert _safe_float("abc") == 0.0


class TestClassifySeverity:
    def test_sunny_is_0(self):
        assert _classify_severity("晴") == 0

    def test_cloudy_is_1(self):
        assert _classify_severity("多云") == 1
        assert _classify_severity("阴") == 1

    def test_light_rain_is_2(self):
        assert _classify_severity("小雨") == 2
        assert _classify_severity("阵雨") == 2

    def test_heavy_rain_is_3(self):
        assert _classify_severity("大雨") == 3

    def test_severe_is_4(self):
        assert _classify_severity("沙尘暴") == 4
        assert _classify_severity("飓风") == 4
        # 暴雨 contains "暴" in SEVERE_KEYWORDS, so it's 4, not 3
        assert _classify_severity("暴雪") == 4

    def test_empty_returns_0(self):
        assert _classify_severity("") == 0


class TestWeatherFactor:
    def test_values(self):
        assert _weather_factor(0) == 1.0
        assert _weather_factor(1) == 0.85
        assert _weather_factor(2) == 0.55
        assert _weather_factor(3) == 0.25
        assert _weather_factor(4) == 0.05


class TestTempFactor:
    def test_ideal(self):
        assert _temp_factor(20) == 1.0

    def test_warm(self):
        assert _temp_factor(30) == 0.85

    def test_hot(self):
        assert _temp_factor(34) == 0.65

    def test_very_hot(self):
        assert _temp_factor(37) == 0.4

    def test_extreme_hot(self):
        assert _temp_factor(40) == 0.2

    def test_cool(self):
        assert _temp_factor(10) == 0.8

    def test_cold(self):
        assert _temp_factor(3) == 0.6

    def test_freezing(self):
        assert _temp_factor(-10) == 0.3


class TestWindFactor:
    def test_calm(self):
        assert _wind_factor(3) == 1.0

    def test_moderate(self):
        assert _wind_factor(5) == 0.9

    def test_strong(self):
        assert _wind_factor(7) == 0.5

    def test_gale(self):
        assert _wind_factor(9) == 0.15


class TestOutdoorSuitability:
    def test_perfect(self):
        result = _compute_outdoor_suitability(0, 22, 2)
        assert 0.9 < result <= 1.0

    def test_severe(self):
        result = _compute_outdoor_suitability(4, 40, 9)
        assert result < 0.01


class TestTrafficSpeedFactor:
    def test_values(self):
        assert _traffic_speed_factor(0) == 1.0
        assert _traffic_speed_factor(2) == 0.85
        assert _traffic_speed_factor(4) == 0.5


class TestIsWalkingViable:
    def test_viable(self):
        assert _is_walking_viable(0, 25, 2) is True

    def test_severe_weather_not_viable(self):
        assert _is_walking_viable(3, 25, 2) is False

    def test_too_hot_not_viable(self):
        assert _is_walking_viable(0, 37, 2) is False


class TestPreferredMode:
    def test_severe_forces_transit(self):
        assert _compute_preferred_mode(3, 25, "walking") == "transit"

    def test_hot_forces_transit(self):
        assert _compute_preferred_mode(1, 36, "walking") == "transit"

    def test_normal_keeps_preferred(self):
        assert _compute_preferred_mode(1, 25, "walking") == "walking"


class TestHeatRisk:
    def test_none(self):
        assert _classify_heat_risk(25) == "none"

    def test_low(self):
        assert _classify_heat_risk(30) == "low"

    def test_medium(self):
        assert _classify_heat_risk(33) == "medium"

    def test_high(self):
        assert _classify_heat_risk(36) == "high"

    def test_extreme(self):
        assert _classify_heat_risk(40) == "extreme"


class TestGenerateAdvice:
    def test_good_weather(self):
        impact = {"outdoor_suitability": 0.9, "severity_grade": 0, "dayweather": "晴",
                  "heat_risk": "none", "walking_viable": True}
        advice = _generate_advice(impact)
        assert any("适合户外" in a for a in advice)

    def test_bad_weather(self):
        impact = {"outdoor_suitability": 0.2, "severity_grade": 3, "dayweather": "暴雨",
                  "heat_risk": "none", "walking_viable": False}
        advice = _generate_advice(impact)
        assert any("室内" in a for a in advice)
        assert any("不建议步行" in a for a in advice)


class TestBuildNeutralImpacts:
    def test_basic(self):
        result = build_neutral_impacts(days=3, start_date="2026-08-01", preferred_transport="地铁")
        assert len(result) == 3
        for day in result:
            assert day["walking_viable"] is True
            assert day["outdoor_suitability"] == 1.0
            assert day["traffic_speed_factor"] == 1.0
            assert day["severity_grade"] == 0

    def test_single_day(self):
        result = build_neutral_impacts(days=1)
        assert len(result) == 1

    def test_different_transport(self):
        result = build_neutral_impacts(days=2, preferred_transport="driving")
        assert result[0]["preferred_mode"] == "driving"


class TestCalculateWeatherImpact:
    def test_with_forecasts(self):
        forecasts = [
            {"date": "2026-08-01", "dayweather": "晴", "nightweather": "多云",
             "daytemp": "30", "nighttemp": "20", "daypower": "2"},
            {"date": "2026-08-02", "dayweather": "小雨", "nightweather": "小雨",
             "daytemp": "25", "nighttemp": "18", "daypower": "3"},
        ]
        result = calculate_weather_impact(forecasts, "transit")
        assert len(result) == 2
        assert result[0]["severity_grade"] == 1  # nightweather "多云" → 1
        assert result[1]["severity_grade"] > 0  # 小雨 = caution (2)
        assert len(result[1]["advice"]) > 0
