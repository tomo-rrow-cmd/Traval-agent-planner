"""
候选增强评分 — 语义相关度 + 评分 + 价格 + 标签匹配 综合排序
"""

from typing import Any


def composite_score(
    candidates: list[dict],
    preferences: list[str] | None = None,
    max_price: float = 0,
    min_rating: float = 0,
    tag_boost: list[str] | None = None,
) -> list[dict]:
    """
    综合评分：relevance*0.5 + rating_norm*0.25 + tag_match*0.15 + price_norm*0.1

    Args:
        candidates: Chroma 返回的候选列表，每项含 relevance/rating/price/tags
        preferences: 用户偏好词列表，用于构建标签 boost
        max_price: 预算上限，超过的打折
        min_rating: 最低评分，不达标的降权
        tag_boost: 额外 boost 的标签

    Returns: 按 composite_score 降序排列的候选列表
    """
    if not candidates:
        return []

    # 从 preferences 自动生成 tag_boost
    if tag_boost is None and preferences:
        tag_boost = _prefs_to_tags(preferences)

    # 归一化
    max_rating = max((c.get("rating", 0) or 0 for c in candidates), default=5)
    max_price_val = max((c.get("price", 0) or c.get("avg_price", 0) or c.get("price_per_night", 0) or 0
                         for c in candidates), default=1)

    for c in candidates:
        # relevance (0-1)
        rel = float(c.get("relevance", c.get("rerank_score", 0.5)) or 0.5)

        # rating (normalized 0-1)
        rating = float(c.get("rating", 0) or 0)
        rating_norm = rating / max_rating if max_rating > 0 else 0

        # tag match
        tags = _parse_tags(c)
        tag_match = _tag_match_score(tags, tag_boost) if tag_boost else 0.5

        # price (lower is better, normalized inverted)
        price = float(c.get("price", 0) or c.get("avg_price", 0) or c.get("price_per_night", 0) or 0)
        price_norm = 1 - (price / max_price_val) if max_price_val > 0 else 0.5

        # penalty for over-budget
        budget_penalty = 0.0
        if max_price > 0 and price > max_price:
            budget_penalty = min(0.3, (price - max_price) / max_price * 0.3)

        # penalty for low rating
        rating_penalty = 0.0
        if min_rating > 0 and rating < min_rating:
            rating_penalty = 0.2

        c["composite_score"] = round(
            rel * 0.50 +
            rating_norm * 0.25 +
            tag_match * 0.15 +
            price_norm * 0.10 -
            budget_penalty -
            rating_penalty,
            4,
        )

    candidates.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
    return candidates


def _prefs_to_tags(preferences: list[str]) -> list[str]:
    """偏好词→标签映射"""
    tag_map = {
        "历史": ["世界遗产", "历史人文", "古迹", "博物馆"],
        "人文": ["历史人文", "博物馆", "文化", "古迹"],
        "自然": ["自然风光", "山水", "森林公园", "湖泊", "海滩"],
        "美食": ["川菜", "粤菜", "火锅", "网红店", "老字号", "小吃"],
        "亲子": ["亲子", "动物园", "海洋馆", "游乐园", "科技馆"],
        "购物": ["购物", "商圈", "步行街"],
        "网红": ["网红打卡", "拍照出片", "网红店"],
        "休闲": ["公园", "园林", "散步", "骑行"],
        "夜景": ["夜景", "灯光", "夜市"],
        "温泉": ["温泉", "SPA", "养生"],
        "登山": ["山", "登山", "徒步"],
        "寺庙": ["寺庙", "教堂", "宗教"],
        "滑雪": ["滑雪", "冰雪"],
    }
    tags = []
    for p in preferences:
        for k, v in tag_map.items():
            if k in p:
                tags.extend(v)
    return list(set(tags)) if tags else preferences


def _parse_tags(candidate: dict) -> list[str]:
    """解析候选的标签字段"""
    raw = candidate.get("tags", "")
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        return [t.strip() for t in raw.split(";") if t.strip()]
    return []


def _tag_match_score(candidate_tags: list[str], boost_tags: list[str]) -> float:
    """标签匹配度 (0-1)"""
    if not boost_tags or not candidate_tags:
        return 0.5
    matches = 0
    for bt in boost_tags:
        for ct in candidate_tags:
            if bt in ct or ct in bt:
                matches += 1
                #模糊匹配
                break
    return min(1.0, matches / max(len(boost_tags), 1))
