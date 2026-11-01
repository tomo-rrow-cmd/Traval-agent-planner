"""
DetailAgent — 定稿后深度扩展

从定稿行程中挑选高评分景点/餐厅，调用美团/高德获取真实详情。

原则：无真实数据则跳过，不编造。
"""

import asyncio
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.third_party.meituan_parser import clean_markdown_text


_ASSISTANT_PHRASES = (
    "小团", "小美", "美团助手", "你好呀", "您好呀", "帮你", "为你", "这就",
    "别担心", "快收藏", "快来看看", "奉上", "想了解",
)
_NO_RESULT_PHRASES = (
    "无结果", "暂无结果", "暂未查询到", "暂时没有查询到", "没有查询到",
    "未查询到", "未找到", "没有找到", "查不到", "无法查询", "无法确认",
    "无法获取", "暂无相关", "没有相关", "建议调整关键词", "建议换关键词",
    "信息不足", "暂不清楚",
)
_ATTR_TIP_LABELS = (
    "游玩注意事项", "注意事项", "温馨提示", "游玩建议", "开放时间",
    "营业时间", "时间与门票", "门票信息", "预约方式", "交通指南",
    "最佳时间", "游玩时间", "注意", "提示", "建议", "开放", "门票",
    "预约", "交通",
)
_ATTR_SPOT_LABELS = (
    "必去景点", "著名景点", "推荐景点", "核心景点", "特色景点",
    "特色体验", "必打卡", "必去", "亮点",
)
_FOOD_DISH_LABELS = (
    "招牌必点", "招牌菜", "推荐菜", "必点菜", "特色菜", "拿手菜",
    "招牌", "必点",
)
_FOOD_REVIEW_LABELS = ("用户评价", "好评", "口碑", "评价", "评分")
_LIST_PREFIX_RE = re.compile(
    r"^\s*(?:[-*+>•·]|\d+[.)、]|[一二三四五六七八九十]+[、.)])\s*"
)
_MARKETING_TAIL_RE = re.compile(
    r"(?:[，。；]\s*)?(?:很多|不少|许多|深受)(?:食客|游客|网友|用户|大家).*$"
)
_PROMO_TAIL_RE = re.compile(
    r"(?:[，。；]\s*)?(?:一定要|值得一试|值得打卡|不要错过|快去|快来).*$"
)
_DISH_BOILERPLATE_RE = re.compile(
    r"(?:是|属于)(?:店里|店内|本店|这家店)(?:的)?(?:招牌|推荐).*$"
)


class DetailAgent(BaseAgent):
    """深度扩展智能体"""

    name = "detail"
    description = "定稿行程 → 挑选亮点 → 获取详情 → 深度攻略"

    # 挑选阈值
    MIN_ATTR_RATING = 4.3
    MIN_FOOD_RATING = 4.2
    MAX_ATTR_DETAIL = 3    # 最多扩展3个景点
    MAX_FOOD_DETAIL = 3    # 最多扩展3家餐厅

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        daily_plan = input_data.get("daily_plan", [])
        meal_plan = input_data.get("meal_plan", [])
        destination = input_data.get("destination", "")

        # ---- 挑选亮点 ----
        attr_picks = self._pick_attractions(daily_plan)
        food_picks = self._pick_restaurants(meal_plan)

        # ---- 并行获取详情 ----
        attr_details = await self._fetch_attr_details(attr_picks, destination)
        food_details = await self._fetch_food_details(food_picks, destination)

        return {
            "attraction_details": attr_details,
            "food_details": food_details,
        }

    # ---- 挑选 ----

    def _pick_attractions(self, daily_plan: list) -> list[dict]:
        all_attrs = []
        for day in daily_plan:
            for a in day.get("attractions", []):
                all_attrs.append({"day": day.get("day", 1), **a})
        # 按评分排序，取Top
        sorted_attrs = sorted(all_attrs, key=lambda x: x.get("rating", 0) or 0, reverse=True)
        return sorted_attrs[:self.MAX_ATTR_DETAIL]

    def _pick_restaurants(self, meal_plan: list) -> list[dict]:
        all_foods = []
        for day in meal_plan:
            for m in day.get("meals", []):
                all_foods.append({"day": day.get("day", 1), **m})
        sorted_foods = sorted(all_foods, key=lambda x: x.get("avg_price", 0) or 0, reverse=True)
        return sorted_foods[:self.MAX_FOOD_DETAIL]

    # ---- 获取详情 ----

    async def _fetch_attr_details(self, picks: list, city: str) -> list[dict]:
        if not picks:
            return []
        tasks = [self._fetch_one_attr(p, city) for p in picks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def _fetch_one_attr(self, attr: dict, city: str) -> dict | None:
        name = attr.get("name", "")
        if not name:
            return None

        detail = {"name": name, "day": attr.get("day", 1), "rating": attr.get("rating", 0)}

        # ---- 美团 CLI ----
        try:
            from app.services.third_party.meituan import meituan
            if meituan.available:
                q = (
                    f"请查询{city}的“{name}”，只返回已确认的信息，按“注意事项：”"
                    "和“必打卡：”逐行输出；无可靠结果仅返回“无结果”；"
                    "不要寒暄、自称或推荐其他城市的同名地点"
                )
                r = await asyncio.wait_for(meituan.query(city, q), timeout=60.0)
                if r.get("success") and r.get("text"):
                    parsed = _parse_attr_text(r["text"])
                    if parsed and _detail_fields_are_clean(parsed):
                        detail.update(parsed)
                        return detail
        except Exception:
            pass

        # ---- 高德 POI 详情兜底 ----
        try:
            from app.services.map.amap import AmapService
            amap = AmapService()
            pois = await amap.search_poi(keywords=name, city=city, offset=1)
            if pois:
                p = pois[0]
                tip = p.get("business_area") or p.get("address", "")
                address = p.get("address", "")
                if tip:
                    detail["tips"] = [tip]
                if address:
                    detail["address"] = address
        except Exception:
            pass

        has_content = any(detail.get(field) for field in ("tips", "famous_spots", "address"))
        return detail if has_content and _detail_fields_are_clean(detail) else None

    async def _fetch_food_details(self, picks: list, city: str) -> list[dict]:
        if not picks:
            return []
        tasks = [self._fetch_one_food(p, city) for p in picks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def _fetch_one_food(self, food: dict, city: str) -> dict | None:
        name = food.get("restaurant", "") or food.get("name", "")
        if not name:
            return None

        detail = {"name": name, "day": food.get("day", 1),
                  "avg_price": food.get("avg_price", 0), "meal": food.get("meal", "")}

        # ---- 美团 CLI ----
        try:
            from app.services.third_party.meituan import meituan
            if meituan.available:
                q = (
                    f"请查询{city}的“{name}”，只返回已确认的信息，按“招牌菜：”"
                    "和“用户评价：”逐行输出；无可靠结果仅返回“无结果”；"
                    "不要寒暄、自称或介绍其他城市的同名门店"
                )
                r = await asyncio.wait_for(meituan.query(city, q), timeout=60.0)
                if r.get("success") and r.get("text"):
                    parsed = _parse_food_text(r["text"])
                    if parsed and _detail_fields_are_clean(parsed):
                        detail.update(parsed)
                        return detail
        except Exception:
            pass

        return detail if "signature_dishes" in detail else None


def _parse_attr_text(text: str) -> dict | None:
    """从美团返回文本提取景点关键信息"""
    return _parse_labeled_text(
        text,
        label_groups={"tips": _ATTR_TIP_LABELS, "famous_spots": _ATTR_SPOT_LABELS},
        limits={"tips": 5, "famous_spots": 5},
    )


def _parse_food_text(text: str) -> dict | None:
    """从美团返回文本提取餐厅关键信息"""
    return _parse_labeled_text(
        text,
        label_groups={
            "signature_dishes": _FOOD_DISH_LABELS,
            "user_feedback": _FOOD_REVIEW_LABELS,
        },
        limits={"signature_dishes": 5, "user_feedback": 3},
    )


def _parse_labeled_text(
    text: str,
    *,
    label_groups: dict[str, tuple[str, ...]],
    limits: dict[str, int],
) -> dict | None:
    if not text or _contains_no_result(text):
        return None

    result = {field: [] for field in label_groups}
    active_field: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or re.fullmatch(r"[-—_=]{3,}", stripped):
            continue

        is_heading = bool(re.match(r"^#{1,6}\s*", stripped))
        line = re.sub(r"^#{1,6}\s*", "", stripped)
        line = _LIST_PREFIX_RE.sub("", line)
        segments = _split_detail_segments(line, label_groups)

        for segment in segments:
            normalized = _normalize_segment(segment)
            if not normalized:
                continue

            matched = _match_labeled_value(normalized, label_groups)
            if matched:
                field, value = matched
                if value:
                    _append_unique(result[field], value, limits[field])
                    active_field = None
                else:
                    active_field = field
                continue

            if active_field:
                value = _clean_detail_value(normalized)
                if value:
                    _append_unique(result[active_field], value, limits[active_field])

        if is_heading and not _match_labeled_value(_normalize_segment(line), label_groups):
            active_field = None

    cleaned = {field: values for field, values in result.items() if values}
    return cleaned if cleaned and _detail_fields_are_clean(cleaned) else None


def _match_labeled_value(
    segment: str,
    label_groups: dict[str, tuple[str, ...]],
) -> tuple[str, str] | None:
    for field, labels in label_groups.items():
        for label in labels:
            match = re.match(rf"^{re.escape(label)}\s*(?:[:：]\s*(.*)|$)", segment)
            if match:
                return field, _clean_detail_value(match.group(1) or "")
    return None


def _split_detail_segments(
    line: str,
    label_groups: dict[str, tuple[str, ...]],
) -> list[str]:
    labels = sorted(
        {label for labels in label_groups.values() for label in labels},
        key=len,
        reverse=True,
    )
    label_pattern = "|".join(re.escape(label) for label in labels)
    separated = re.sub(
        rf"(?<=[。！？!?、，,])\s*(?=(?:{label_pattern})\s*[:：])",
        "；",
        line,
    )
    return [segment for segment in re.split(r"[；;]+", separated) if segment.strip()]


def _normalize_segment(value: str) -> str:
    text = clean_markdown_text(value)
    text = re.sub(r"^[\s>*•·\-–—✅⭐🌟💡🔍📌🍽️]+", "", text)
    return text.strip()


def _clean_detail_value(value: str) -> str:
    text = _normalize_segment(value)
    if not text or _contains_blocked_text(text):
        return ""
    text = _MARKETING_TAIL_RE.sub("", text)
    text = _PROMO_TAIL_RE.sub("", text)
    text = _DISH_BOILERPLATE_RE.sub("", text)
    return text.strip(" ，。；;：:～~")[:120]


def _append_unique(values: list[str], value: str, limit: int) -> None:
    if value and value not in values and len(values) < limit:
        values.append(value)


def _contains_no_result(value: str) -> bool:
    text = clean_markdown_text(value)
    return any(phrase in text for phrase in _NO_RESULT_PHRASES)


def _contains_blocked_text(value: str) -> bool:
    text = clean_markdown_text(value)
    return _contains_no_result(text) or any(phrase in text for phrase in _ASSISTANT_PHRASES)


def _detail_fields_are_clean(detail: dict) -> bool:
    for field in ("tips", "famous_spots", "signature_dishes", "user_feedback", "address"):
        value = detail.get(field)
        items = value if isinstance(value, list) else [value]
        if any(item and _contains_blocked_text(str(item)) for item in items):
            return False
    return True
