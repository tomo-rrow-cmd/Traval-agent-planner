"""
纪念品推荐智能体 — LLM 生成特产推荐（无需向量库）

纪念品数据不适合 POI 搜索，直接用 LLM 知识 + 城市信息生成推荐。
"""

import json, re
from typing import Any
from app.agents.base import BaseAgent


class SouvenirAgent(BaseAgent):
    """纪念品推荐智能体"""

    name = "souvenir"
    description = "LLM 根据目的地和预算生成特产/纪念品推荐"

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        destination = input_data.get("destination", "")
        preferences = input_data.get("preferences", [])
        remaining_budget = input_data.get("remaining_budget", 500)
        travelers = input_data.get("travelers", 1)

        prompt = f"""你是{destination}特产/纪念品推荐专家。
用户偏好：{'、'.join(preferences) if preferences else '通用'}，
剩余购物预算：¥{remaining_budget}（{travelers}人）。

推荐5-8个{destination}值得买的特产或纪念品：
- 兼顾地方特色和实用性
- 标注参考价格和推荐购买地点
- 总花费控制在 ¥{remaining_budget} 以内

只返回 JSON：
{{"souvenirs":[
  {{"name":"商品名","category":"食品/工艺品/日用品等",
    "price_range":"¥50-100","buy_place":"购买地点或区域",
    "reason":"推荐理由一句话","quantity_suggest":2}}
],
"total_estimate":总价估算}}"""

        try:
            response = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.7)
            return json.loads(_extract_json(response))
        except Exception as e:
            print(f"  [Souvenir LLM] 失败: {e}")
            return {"souvenirs": [], "total_estimate": 0, "message": f"生成失败: {e}"}


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m: return m.group(1).strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m: return m.group(0).strip()
    return text.strip()
