"""
PhotoPlannerAgent — 用户上传旅行照片 → AI 看图提取偏好 → 生成方案

流程:
    1. 接收用户照片 URL 列表 + 可选文字描述
    2. Vision 模型分析照片：提取目的地线索、偏好、节奏、氛围
    3. 喂给 UserInteractionAgent 做参数确认
    4. 返回 extracted 参数，对接现有 pipeline

用法:
    agent = PhotoPlannerAgent(llm)
    result = await agent.run({
        "images": ["https://...", "https://..."],
        "user_message": "想去这样的地方",  # 可选
    })
    # → result["extracted"] 可直接喂给 run_pipeline()
"""

from typing import Any

from app.agents.base import BaseAgent
from app.services.llm.base import BaseLLM


class PhotoPlannerAgent(BaseAgent):
    """看图规划 — Vision 提取偏好 + LLM 对话确认"""

    name = "photo_planner"
    description = "User uploads travel photos → Vision extracts preferences → generate plan"

    def __init__(self, llm: BaseLLM):
        super().__init__(llm)
        self._vision = None

    @property
    def vision(self):
        if self._vision is None:
            try:
                from app.services.llm.vision import vision_llm
                self._vision = vision_llm
            except Exception:
                self._vision = False
        return self._vision if self._vision is not False else None

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        images = input_data.get("images", [])
        user_message = input_data.get("user_message", "")
        history = input_data.get("history", [])  # 已有的对话确认历史

        if not images:
            return {"error": "至少需要一张照片", "status": "no_images"}

        # ---- 1. Vision 分析照片 ----
        scene_info = {}
        if self.vision:
            try:
                scene_info = await self.vision.extract_preferences(images, user_message)
            except Exception as e:
                print(f"  [PhotoPlanner] Vision 分析失败: {e}")

        # ---- 2. 构建确认话术 ----
        destination_hint = scene_info.get("destination_hint", "")
        scene_summary = scene_info.get("scene_summary", "")
        preferences = scene_info.get("preferences", [])
        pace = scene_info.get("pace", "适中")
        vibe = scene_info.get("vibe", "休闲")

        # 组装 extracted 参数
        extracted = {
            "destination": "",  # 需要用户确认
            "origin": "",       # 需要用户补充
            "days": 3,
            "total_budget": 5000,
            "preferences": preferences,
            "preferences_provided": bool(preferences),
            "pace": pace,
        }

        # 构建自然语言确认消息
        if destination_hint or scene_summary or preferences:
            pref_text = "、".join(preferences) if preferences else "待确认"
            dest_part = f"目的地可能是{destination_hint}" if destination_hint else ""
            summary_part = f"看起来{scene_summary}" if scene_summary else ""
            reply = (
                f"看了你发的{len(images)}张照片，{summary_part}。{dest_part}。"
                f"推测偏好：{pref_text}，节奏偏{pace}。"
                f"你想去哪里？从哪个城市出发？玩几天？预算多少？"
            )
        else:
            reply = (
                f"我看了你发的{len(images)}张照片，但不太确定你的偏好。"
                f"你能告诉我想去哪里、从哪出发、预算多少吗？"
            )

        return {
            "reply": reply,
            "mode": "travel_planning",
            "status": "collecting",
            "extracted": extracted,
            "scene_info": scene_info,
            "image_count": len(images),
            "confirmed": False,
            "ready": False,
        }

    async def run_with_confirm(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        直接一步到位：Vision 提取 → 用户参数补全 → 返回可直接喂 pipeline 的参数。
        前提是 input_data 中已经包含了完整的用户参数。
        """
        result = await self.run(input_data)

        # 合并用户已提供的参数
        result["extracted"]["destination"] = input_data.get("destination", "")
        result["extracted"]["origin"] = input_data.get("origin", "")
        result["extracted"]["days"] = input_data.get("days", 3)
        result["extracted"]["total_budget"] = input_data.get("total_budget", 5000)

        # 如果参数齐全，标记 ready
        ex = result["extracted"]
        if ex["destination"] and ex["origin"] and ex["days"] > 0 and ex["total_budget"] > 0:
            result["ready"] = True
            result["confirmed"] = True
            result["reply"] = (
                f"好的！从照片看，你喜欢{ex.get('preferences', ['自然风光'])}。"
                f"开始规划 {ex['origin']}→{ex['destination']} {ex['days']}天方案。"
            )

        return result
