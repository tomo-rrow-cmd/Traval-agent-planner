"""测试 app/agents/food_agent.py — 模块级纯函数"""

import pytest
from app.agents.food_agent import (
    _extract_json,
    _fallback_meals,
    _name_key,
    _rank_score,
    _attach_candidate_data,
)


class TestExtractJson:
    def test_extracts_from_code_block(self):
        text = '```json\n{"meal_plan": [{"day": 1}]}\n```'
        result = _extract_json(text)
        assert '"meal_plan"' in result

    def test_extracts_from_bare_code_block(self):
        text = '```\n{"meal_plan": []}\n```'
        result = _extract_json(text)
        assert '"meal_plan"' in result

    def test_extracts_bare_json(self):
        text = 'some text {"key": "value"} more text'
        result = _extract_json(text)
        assert result == '{"key": "value"}'

    def test_no_json_returns_raw_text(self):
        text = "plain text without json"
        result = _extract_json(text)
        assert result == text

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = _extract_json(text)
        assert '"inner"' in result


class TestFallbackMeals:
    def test_allocates_by_day(self):
        candidates = [
            {"name": f"餐厅{i}", "rating": 5.0 - i * 0.2, "avg_price": 100 - i * 5}
            for i in range(10)
        ]
        plan = _fallback_meals(candidates, 3)
        assert len(plan) == 3
        assert plan[0]["day"] == 1
        assert len(plan[0]["meals"]) == 2  # lunch + dinner
        assert plan[0]["meals"][0]["meal"] == "午餐"
        assert plan[0]["meals"][1]["meal"] == "晚餐"

    def test_fewer_candidates_than_days(self):
        candidates = [
            {"name": "仅此一家", "rating": 4.5, "avg_price": 80},
        ]
        plan = _fallback_meals(candidates, 5)
        assert len(plan) == 5
        # 第一天有午餐（唯一候选），后续天可能没有
        assert len(plan[0]["meals"]) == 1

    def test_empty_candidates(self):
        plan = _fallback_meals([], 3)
        assert len(plan) == 3
        assert all(len(d["meals"]) == 0 for d in plan)


class TestNameKey:
    def test_normalizes_chinese_parentheses(self):
        # _name_key 会去掉括号及其内容，只保留括号前的名称
        result = _name_key("海底捞（王府井店）")
        assert result == "海底捞"

    def test_strips_whitespace(self):
        assert _name_key("  全聚德  (前门店)  ") == "全聚德"

    def test_lowercase(self):
        assert _name_key("McDonalds") == "mcdonalds"


class TestRankScore:
    def test_uses_rerank_score_if_present(self):
        assert _rank_score({"rerank_score": 0.85, "relevance": 0.5}) == 0.85

    def test_falls_back_to_relevance(self):
        assert _rank_score({"relevance": 0.6}) == 0.6

    def test_returns_zero_if_both_missing(self):
        assert _rank_score({}) == 0


class TestAttachCandidateData:
    def test_copies_fields_to_meal_entries(self):
        meal_plan = [
            {"day": 1, "meals": [
                {"restaurant": "海底捞", "avg_price": 0},
                {"restaurant": "不存在", "avg_price": 0},
            ]},
        ]
        candidates = [
            {"name": "海底捞", "poi_id": "poi-001", "rating": 4.5,
             "avg_price": 120, "latitude": 39.9, "longitude": 116.4,
             "source": "rag", "source_poi_id": "s1", "address": "中关村"},
        ]
        _attach_candidate_data(meal_plan, candidates)

        assert meal_plan[0]["meals"][0]["poi_id"] == "poi-001"
        assert meal_plan[0]["meals"][0]["rating"] == 4.5
        assert meal_plan[0]["meals"][0]["latitude"] == 39.9
        # 不存在的餐厅不被更新
        assert "poi_id" not in meal_plan[0]["meals"][1]

    def test_no_candidates(self):
        meal_plan = [{"day": 1, "meals": [{"restaurant": "任意"}]}]
        _attach_candidate_data(meal_plan, [])
        # 不应该崩溃
        assert "poi_id" not in meal_plan[0]["meals"][0]
