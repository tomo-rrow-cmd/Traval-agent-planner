"""测试 app/utils/validator.py — 数据校验工具"""

import pytest
from datetime import date

from app.utils.validator import (
    resolve_trip_dates,
    validate_date_range,
    validate_budget,
    sanitize_input,
    validate_required_fields,
)


class TestValidateDateRange:
    def test_valid_range_returns_true(self):
        is_valid, msg = validate_date_range("2026-07-20", "2026-07-25", today=date(2026, 7, 16))
        assert is_valid is True
        assert msg == ""

    def test_past_start_date_returns_false(self):
        is_valid, msg = validate_date_range("2020-01-01", "2026-07-25")
        assert is_valid is False
        assert "不能早于今天" in msg

    def test_end_before_start_returns_false(self):
        is_valid, msg = validate_date_range("2026-07-25", "2026-07-20", today=date(2026, 7, 16))
        assert is_valid is False
        assert "不能早于出发" in msg

    def test_exceeds_30_days_returns_false(self):
        is_valid, msg = validate_date_range("2026-08-01", "2026-09-15", today=date(2026, 7, 16))
        assert is_valid is False
        assert "30 天" in msg

    @pytest.mark.parametrize("bad_input", [
        "not-a-date",
        "07-20-2026",
        "2026/07/20",
    ])
    def test_invalid_format_returns_false(self, bad_input):
        is_valid, msg = validate_date_range(bad_input, "2026-08-25", today=date(2026, 7, 16))
        assert is_valid is False
        assert "格式无效" in msg

    def test_exactly_30_days_returns_true(self):
        """刚好 30 天应该通过"""
        is_valid, msg = validate_date_range("2026-08-01", "2026-08-30", today=date(2026, 7, 16))
        assert is_valid is True


class TestResolveTripDates:
    today = date(2026, 7, 16)

    def test_start_date_and_days_derives_end_date(self):
        result = resolve_trip_dates("2026-08-01", days=3, today=self.today)
        assert result == {
            "ok": True,
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
            "days": 3,
        }

    def test_start_and_end_derives_inclusive_days(self):
        result = resolve_trip_dates("2026-08-01", "2026-08-05", today=self.today)
        assert result["ok"] is True
        assert result["days"] == 5

    def test_date_range_and_days_conflict(self):
        result = resolve_trip_dates("2026-08-01", "2026-08-05", 3, today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "date_days_conflict"
        assert result["provided_days"] == 3
        assert result["derived_days"] == 5

    def test_missing_start_date(self):
        result = resolve_trip_dates("", "2026-08-05", 5, today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "missing_start_date"

    def test_past_start_date(self):
        result = resolve_trip_dates("2026-07-15", days=3, today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "past_start_date"

    def test_reverse_date(self):
        result = resolve_trip_dates("2026-08-05", "2026-08-01", today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "end_before_start"

    def test_invalid_format(self):
        result = resolve_trip_dates("2026/08/01", days=3, today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "invalid_format"

    def test_31_days_exceeds_limit(self):
        result = resolve_trip_dates("2026-08-01", "2026-08-31", today=self.today)
        assert result["ok"] is False
        assert result["error_code"] == "exceeds_max_days"


class TestValidateBudget:
    def test_reasonable_budget_returns_true(self):
        is_valid, msg = validate_budget(5000, 5, 2)
        assert is_valid is True
        assert msg == ""

    def test_zero_budget_returns_false(self):
        is_valid, msg = validate_budget(0, 5, 2)
        assert is_valid is False
        assert "必须大于 0" in msg

    def test_negative_budget_returns_false(self):
        is_valid, msg = validate_budget(-100, 5, 2)
        assert is_valid is False
        assert "必须大于 0" in msg

    def test_below_per_person_per_day_threshold_returns_false(self):
        is_valid, msg = validate_budget(500, 5, 2)  # 50/人/天 < 100
        assert is_valid is False
        assert "过低" in msg

    def test_exactly_at_threshold_returns_false(self):
        is_valid, msg = validate_budget(999, 5, 2)  # ~99.9/人/天
        assert is_valid is False
        assert "过低" in msg

    def test_zero_travelers_falls_back_to_raw_budget(self):
        """travelers=0 时 per_person_per_day = budget，检查不低于100即可"""
        is_valid, msg = validate_budget(200, 5, 0)  # 200 per person
        assert is_valid is True

    def test_zero_days_and_travelers_falls_back(self):
        is_valid, msg = validate_budget(200, 0, 0)  # 200 total > 100 threshold
        assert is_valid is True


class TestSanitizeInput:
    def test_normal_text_unchanged(self):
        assert sanitize_input("你好，我想去北京") == "你好，我想去北京"

    def test_strips_whitespace(self):
        assert sanitize_input("   hello world   ") == "hello world"

    def test_empty_string_returns_empty(self):
        assert sanitize_input("") == ""

    def test_none_returns_empty(self):
        assert sanitize_input(None) == ""

    def test_truncates_at_max_length(self):
        result = sanitize_input("1234567890", max_length=5)
        assert len(result) == 5
        assert result == "12345"

    def test_default_max_length_is_500(self):
        long_text = "a" * 600
        result = sanitize_input(long_text)
        assert len(result) == 500

    def test_shorter_than_max_length_unchanged(self):
        assert sanitize_input("hello", max_length=100) == "hello"


class TestValidateRequiredFields:
    def test_all_present_returns_empty(self):
        missing = validate_required_fields(
            {"name": "Alice", "email": "a@b.com"},
            ["name", "email"],
        )
        assert missing == []

    def test_some_missing_returns_missing_keys(self):
        missing = validate_required_fields(
            {"name": "Alice"},
            ["name", "email", "phone"],
        )
        assert missing == ["email", "phone"]

    def test_all_missing_returns_all_keys(self):
        missing = validate_required_fields(
            {"other": "value"},
            ["name", "email"],
        )
        assert missing == ["name", "email"]

    def test_empty_data_returns_all_keys(self):
        missing = validate_required_fields({}, ["name"])
        assert missing == ["name"]

    def test_empty_required_list_returns_empty(self):
        missing = validate_required_fields({"name": "Alice"}, [])
        assert missing == []

    def test_falsy_values_count_as_missing(self):
        """空字符串、0、None 等 falsy 值视为缺失"""
        missing = validate_required_fields(
            {"name": "", "count": 0, "flag": False},
            ["name", "count", "flag"],
        )
        assert "name" in missing
        assert "count" in missing
        assert "flag" in missing
