"""
TravelogueAgent — 游记生成 + 照片整理 + 社交素材

功能:
- 基于签到数据 + 用户备注 + 照片 → AI 润色生成游记
- 照片自动标注（AI caption + tags + 质量评分）
- 朋友圈9宫格/旅行卡片/精选合集素材生成
- 多风格支持（日记风/小红书风/攻略向）
"""

import asyncio
import random
import secrets
import string
from datetime import datetime
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm.base import BaseLLM


def _style_label(style: str) -> str:
    return {
        "diary": "日记风",
        "xiaohongshu": "小红书风",
        "guide": "攻略风",
    }.get(style, "日记风")


class TravelogueAgent(BaseAgent):
    name = "travelogue"
    description = "游记生成 + 照片整理 + 社交素材"

    def __init__(self, llm: BaseLLM):
        super().__init__(llm)
        self.photo_organizer = PhotoOrganizer(llm)

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        action = input_data.get("action", "generate")
        if action == "generate":
            return await self.generate(input_data)
        elif action == "regenerate_section":
            return await self.regenerate_section(input_data)
        elif action == "generate_materials":
            return await self.generate_social_materials(input_data)
        elif action == "annotate_photos":
            return await self.annotate_photos(input_data)
        return {"error": f"Unknown action: {action}"}

    # ========== 游记生成 ==========

    async def generate(self, data: dict) -> dict:
        """基于整份方案与实际记录，按天生成一篇完整游记初稿。"""
        checkins = [item for item in data.get("checkins", []) if isinstance(item, dict)]
        style = data.get("style", "diary")
        trip_info = data.get("trip_info", {}) if isinstance(data.get("trip_info"), dict) else {}
        destination = str(trip_info.get("destination") or "这段旅程")
        daily_itinerary = [
            item for item in trip_info.get("daily_itinerary", [])
            if isinstance(item, dict)
        ]
        total_days = max(
            int(trip_info.get("total_days") or 0),
            len(daily_itinerary),
            max((int(item.get("source_day") or item.get("day") or 1) for item in checkins), default=1),
        )

        by_day: dict[int, list[dict]] = {}
        for checkin in checkins:
            day = max(int(checkin.get("source_day") or checkin.get("day") or 1), 1)
            by_day.setdefault(day, []).append(checkin)

        plan_by_day = {
            max(int(item.get("day") or index), 1): item
            for index, item in enumerate(daily_itinerary, start=1)
        }
        day_specs = [
            (day, plan_by_day.get(day, {}), by_day.get(day, []))
            for day in range(1, total_days + 1)
        ]
        content_tasks = [
            asyncio.create_task(asyncio.wait_for(
                self._generate_day_content(
                    day=day,
                    planned_day=planned_day,
                    checkins=day_checkins,
                    style=style,
                    destination=destination,
                ),
                timeout=30,
            ))
            for day, planned_day, day_checkins in day_specs
        ]
        title_task = asyncio.create_task(self._generate_title(destination, total_days, style))
        generated_contents = await asyncio.gather(*content_tasks, return_exceptions=True)
        title_result = await asyncio.gather(title_task, return_exceptions=True)
        title = (
            title_result[0]
            if title_result and isinstance(title_result[0], str) and title_result[0].strip()
            else f"{destination}{total_days}日旅行手记"
        )

        day_contents = []
        all_photos = []
        for (day, planned_day, day_checkins), generated in zip(day_specs, generated_contents):
            if isinstance(generated, Exception):
                content = self._fallback_day_content(
                    day, planned_day, day_checkins, destination,
                )
            else:
                content = generated
            day_photos = [
                photo
                for checkin in day_checkins
                for photo in (checkin.get("photos") or [])
                if isinstance(photo, dict)
            ]
            all_photos.extend(day_photos)
            day_contents.append({
                "day": day,
                "date": planned_day.get("date", ""),
                "content": content,
                "poi_count": len(day_checkins),
                "photos": day_photos[:10],
                "day_cost": round(sum(float(item.get("actual_cost") or 0) for item in day_checkins), 2),
            })

        total_cost = round(float(trip_info.get("actual_total_cost") or 0), 2)

        # 推荐封面（智能选图，而非取第一张）
        cover_url = ""
        cover_info = await self.photo_organizer.select_cover(all_photos) if all_photos else None
        if cover_info:
            cover_url = cover_info.get("url", "")

        # 完整 Markdown
        full_content = self._assemble_content(day_contents, style, destination)

        return {
            "title": title,
            "content": full_content,
            "cover_url": cover_url,
            "style": style,
            "total_days": total_days,
            "total_pois": len(checkins),
            "total_cost": total_cost,
            "total_photos": len(all_photos),
            "photos": [p.get("url", "") for p in all_photos[:20]],
            "day_contents": day_contents,
        }

    async def regenerate_section(self, data: dict) -> dict:
        """局部重写某天内容"""
        day = data.get("day", 1)
        checkins = data.get("checkins", [])
        style = data.get("style", "diary")
        feedback = data.get("feedback", "")

        content = await self._generate_day_content(
            day=day, checkins=checkins, style=style,
            destination=data.get("destination", ""),
            planned_day=data.get("planned_day", {}),
            extra_instruction=f"用户反馈: {feedback}",
        )
        return {"day": day, "content": content}

    # ========== 社交素材 ==========

    async def generate_social_materials(self, data: dict) -> dict:
        """一键生成全套社交素材"""
        trip_id = data.get("trip_id", "")
        checkins = data.get("checkins", [])
        trip_info = data.get("trip_info", {})

        by_day: dict[int, list] = {}
        for c in checkins:
            day = c.get("source_day", c.get("day", 1))
            by_day.setdefault(day, []).append(c)

        materials = []

        # 每天生成 9宫格 + 旅行卡片（独立容错）
        for day in sorted(by_day.keys()):
            day_checkins = by_day[day]
            try:
                grid9 = await self.photo_organizer.generate_daily_9grid(
                    trip_id, day, day_checkins, trip_info)
                if grid9:
                    materials.append(grid9)
            except Exception as e:
                print(f"  [TravelogueAgent] Day {day} 9宫格生成失败: {e}")

            try:
                card = await self.photo_organizer.generate_travel_card(
                    trip_id, day, day_checkins, trip_info)
                if card:
                    materials.append(card)
            except Exception as e:
                print(f"  [TravelogueAgent] Day {day} 卡片生成失败: {e}")

        # 全程精选合集
        try:
            highlight = await self.photo_organizer.generate_trip_highlight(
                trip_id, checkins, trip_info)
            if highlight:
                materials.append(highlight)
        except Exception as e:
            print(f"  [TravelogueAgent] 精选合集生成失败: {e}")

        # 花费总结卡
        try:
            budget_card = await self.photo_organizer.generate_budget_card(trip_info)
            if budget_card:
                materials.append(budget_card)
        except Exception as e:
            print(f"  [TravelogueAgent] 预算卡生成失败: {e}")

        return {"materials": [m for m in materials if m]}

    async def annotate_photos(self, data: dict) -> dict:
        """为签到照片做 AI 标注"""
        checkin_data = data.get("checkin", {})
        return await self.photo_organizer.process_checkin_photos(checkin_data)

    # ================================================================
    #  内容生成
    # ================================================================

    async def _generate_day_content(
        self,
        day: int,
        checkins: list,
        style: str,
        destination: str,
        planned_day: dict | None = None,
        extra_instruction: str = "",
    ) -> str:
        planned_day = planned_day or {}
        actual_lines = []
        for c in checkins:
            poi = c.get("poi_name", "")
            note = c.get("note", "")
            rating = c.get("rating", 0)
            time_str = c.get("actual_at", "") or ""
            photos = c.get("photos", [])
            photo_count = len(photos) if photos else 0
            ai_captions = [p.get("ai_caption", "") for p in (photos or []) if p.get("ai_caption")]
            detail = f"- {poi}"
            if time_str:
                detail += f"，实际时间 {time_str}"
            if rating:
                detail += f"，评分 {rating}/5"
            if note:
                detail += f"，用户备注：{note}"
            detail += f"，{photo_count}张照片"
            actual_lines.append(detail)
            if ai_captions:
                actual_lines.append(f"  照片描述：{'; '.join(ai_captions[:3])}")

        planned_stops = self._planned_stops(planned_day)
        actual_names = {str(item.get("poi_name") or "").strip() for item in checkins}
        unconfirmed_stops = [name for name in planned_stops if name not in actual_names]

        style_guide = {
            "diary": "日记风格 — 第一人称叙述，真实感受，自然随意，像和朋友聊天",
            "xiaohongshu": "小红书风格 — 活泼有趣，带emoji，短句多，有标签感，适合种草",
            "guide": "攻略风格 — 实用信息优先，交通/门票/时间/避坑，结构化清晰",
        }

        prompt = f"""写一段旅行游记（{style_guide.get(style, style_guide['diary'])}）

目的地: {destination}，第 {day} 天
原计划安排:
{chr(10).join(f'- {name}' for name in planned_stops) or '- 无'}

实际签到记录:
{chr(10).join(actual_lines) or '- 无'}

尚未确认实际到访的计划点:
{chr(10).join(f'- {name}' for name in unconfirmed_stops) or '- 无'}

要求:
- 150-300字
- 只允许把“实际签到记录”写成已经发生的体验
- 对尚未确认的计划点只能使用“原计划安排、计划前往、行程中预留”等中性措辞
- 不得虚构用户感受、消费、照片、到访或评价
- 有实际签到时，以签到为线索串联成自然故事；无签到时写成清晰的可编辑行程初稿
- 有照片的地方自然带过"拍了张..."
- {extra_instruction}"""

        try:
            generated = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.8)
        except Exception:
            return self._fallback_day_content(day, planned_day, checkins, destination)

        actual_records = self._actual_records_markdown(checkins)
        if not checkins:
            return f"> 本日暂无实际签到记录，以下为根据原行程生成的可编辑初稿。\n\n{generated}"
        if unconfirmed_stops:
            return (
                f"> 本日记录了 {len(checkins)} 个实际打卡点；其余内容仅作原计划参考。"
                f"\n\n{generated}{actual_records}"
            )
        return f"{generated}{actual_records}"

    async def _generate_title(self, destination: str, days: int, style: str) -> str:
        prompt = f"为{destination}{days}天旅行游记起5个标题（{style}风格，8-20字，吸引眼球）。只返回标题列表。"
        try:
            titles = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.9)
            lines = [t.strip().lstrip("0123456789. -") for t in titles.split("\n") if t.strip()]
            return lines[0] if lines else f"{destination}{days}日游记"
        except Exception:
            return f"{destination}{days}日游记"

    def _assemble_content(self, day_contents: list, style: str, destination: str) -> str:
        lines = []

        for dc in day_contents:
            lines.append(f"## Day {dc['day']}")
            lines.append("")
            lines.append(dc["content"])
            lines.append("")
            # 嵌入配图
            for i, p in enumerate(dc.get("photos", [])[:5]):
                url = p.get("url", "") or p.get("thumbnail_url", "")
                caption = p.get("ai_caption", "") or p.get("caption", "")
                if url:
                    lines.append(f"![{caption}]({url})")
            lines.append("")

        lines.append("---")
        lines.append(
            f"*{destination}整趟旅行游记 · {_style_label(style)} · AI生成初稿，可编辑*"
        )
        return "\n".join(lines)

    def _fallback_day_content(
        self,
        day: int,
        planned_day: dict,
        checkins: list,
        destination: str,
    ) -> str:
        names = [c.get("poi_name", "") for c in checkins[:5] if c.get("poi_name")]
        notes = [c.get("note", "") for c in checkins if c.get("note")]
        if names:
            note_text = f"特别记录：{'；'.join(notes[:2])}。" if notes else ""
            return f"第{day}天在{destination}实际记录了{'、'.join(names)}。{note_text}"
        planned_names = self._planned_stops(planned_day)
        planned_text = "、".join(planned_names) if planned_names else "按当天安排自由探索"
        return (
            "> 本日暂无实际签到记录，以下为根据原行程生成的可编辑初稿。\n\n"
            f"第{day}天的原计划包括{planned_text}，具体体验可在旅行后继续补充。"
        )

    @staticmethod
    def _planned_stops(planned_day: dict) -> list[str]:
        stops = []
        for activity in planned_day.get("activities") or planned_day.get("attractions") or []:
            if isinstance(activity, dict):
                name = activity.get("title") or activity.get("name")
                if name:
                    stops.append(str(name))
        for meal in planned_day.get("meals") or []:
            if isinstance(meal, dict):
                name = meal.get("restaurant") or meal.get("name")
                if name:
                    stops.append(str(name))
        return list(dict.fromkeys(stops))

    @staticmethod
    def _actual_records_markdown(checkins: list[dict]) -> str:
        if not checkins:
            return ""
        lines = ["", "", "### 实际记录"]
        for checkin in checkins:
            poi_name = str(checkin.get("poi_name") or "实际打卡点")
            details = []
            if checkin.get("rating"):
                details.append(f"评分 {checkin['rating']}/5")
            if checkin.get("note"):
                details.append(f"备注：{checkin['note']}")
            if checkin.get("actual_cost") is not None:
                details.append(f"实际花费 ¥{float(checkin['actual_cost']):.0f}")
            suffix = f" · {'；'.join(details)}" if details else ""
            lines.append(f"- **{poi_name}**{suffix}")
        return "\n".join(lines)


# ================================================================
#  PhotoOrganizer — 照片整理 + 社交素材生成
# ================================================================

class PhotoOrganizer:
    """签到照片 → AI标注 + 9宫格 + 旅行卡片 + 精选合集"""

    def __init__(self, llm: BaseLLM):
        self.llm = llm
        self._vision = None

    @property
    def vision(self):
        """延迟加载 VisionLLM，避免启动时依赖"""
        if self._vision is None:
            try:
                from app.services.llm.vision import vision_llm
                self._vision = vision_llm
            except Exception:
                self._vision = False
        return self._vision if self._vision is not False else None

    # ========== 照片标注 ==========

    async def process_checkin_photos(self, checkin: dict) -> dict:
        """为签到照片批量标注 — Vision 优先，文本兜底"""
        photos = checkin.get("photos", []) or []
        poi_name = checkin.get("poi_name", "")
        poi_type = checkin.get("poi_type", "")

        annotated = []
        for p in photos:
            url = p.get("url", "")
            # ---- Vision 模型看图标注 ----
            await self._annotate_with_vision(p, poi_name, poi_type)
            # ---- 兜底：文本模型猜描述 ----
            if not p.get("ai_caption"):
                p["ai_caption"] = await self._ai_caption_text(url, poi_name, poi_type)
            if not p.get("ai_tags"):
                p["ai_tags"] = await self._ai_tags_text(url, poi_name, poi_type)
            if not p.get("aesthetic_score"):
                p["aesthetic_score"] = self._estimate_quality(p)
                p["quality_score"] = p["aesthetic_score"]

            annotated.append({
                **p,
                "is_portrait": p.get("height", 0) > p.get("width", 0),
            })

        return {"photos": annotated, "poi_name": poi_name}

    async def _annotate_with_vision(self, photo: dict, poi_name: str, poi_type: str) -> None:
        """使用 Vision 模型真实看图"""
        url = photo.get("url", "")
        if not url or not self.vision:
            return
        try:
            result = await self.vision.caption_photo(url, poi_name, poi_type)
            photo["ai_caption"] = result.get("caption", "")
            photo["ai_tags"] = result.get("tags", [])
            photo["scene"] = result.get("scene", "")
            photo["mood"] = result.get("mood", "")
            photo["has_people"] = result.get("has_people", False)
            photo["aesthetic_score"] = result.get("aesthetic_score", 4.0)
            photo["quality_score"] = photo["aesthetic_score"]
        except Exception as e:
            print(f"  [PhotoOrganizer] Vision 标注失败: {e}")

    async def _ai_caption_text(self, url: str, poi_name: str, poi_type: str) -> str:
        """纯文本猜描述（Vision 不可用时兜底）"""
        prompt = f"给一张在{poi_name}（{poi_type}）拍摄的旅行照片写一句中文描述（15-30字，文艺感）。"
        try:
            return await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.8)
        except Exception:
            return f"在{poi_name}的美好时刻"

    async def _ai_tags_text(self, url: str, poi_name: str, poi_type: str) -> list[str]:
        """纯文本猜标签（Vision 不可用时兜底）"""
        prompt = f"给一张在{poi_name}（{poi_type}）的旅行照片打5-8个中文标签，逗号分隔。只返回标签。"
        try:
            result = await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.6)
            return [t.strip() for t in result.replace("，", ",").split(",") if t.strip()][:8]
        except Exception:
            return ["旅行", poi_name, "打卡"]

    def _estimate_quality(self, photo: dict) -> float:
        """基于尺寸的简单质量估算（Vision 不可用时兜底）"""
        score = 0.8
        w = photo.get("width", 0)
        h = photo.get("height", 0)
        if w > 2000 and h > 2000:
            score += 0.05
        if w > 3000 or h > 3000:
            score += 0.05
        return min(0.95, round(score, 2))

    # ========== 封面选图 ==========

    async def select_cover(self, photos: list[dict]) -> dict | None:
        """
        从照片列表中选出最佳游记封面。

        Vision 路径：批量评分 → 选最高分
        兜底路径：按尺寸 + 是否有 ai_caption 排序
        """
        if not photos:
            return None

        # Vision 评分
        if self.vision:
            urls = [p.get("url", "") for p in photos if p.get("url")]
            if urls:
                try:
                    scored = await self.vision.score_photos(urls)
                    if scored:
                        # 找最高分的原图
                        best_url = scored[0]["url"]
                        for p in photos:
                            if p.get("url") == best_url:
                                return {
                                    **p,
                                    "cover_reason": scored[0].get("reason", ""),
                                    "cover_score": scored[0].get("score", 4.0),
                                }
                except Exception as e:
                    print(f"  [PhotoOrganizer] 封面选图失败: {e}")

        # 兜底：尺寸最大的优先
        best = max(photos, key=lambda p: (
            p.get("aesthetic_score", 0) or p.get("quality_score", 0),
            (p.get("width", 0) or 0) * (p.get("height", 0) or 0),
        ))
        return {**best, "cover_reason": "尺寸最优", "cover_score": best.get("aesthetic_score", 4.0)}

    # ========== 9宫格素材 ==========

    async def generate_daily_9grid(self, trip_id: str, day: int,
                                    day_checkins: list, trip_info: dict) -> dict:
        """生成朋友圈9宫格"""
        # 收集当天所有照片
        all_photos = []
        for c in day_checkins:
            for p in (c.get("photos", []) or []):
                all_photos.append({**p, "poi_name": c.get("poi_name", "")})

        if not all_photos:
            return None

        # 按质量选9张（不够就全选 + 留白）
        sorted_photos = sorted(all_photos, key=lambda p: p.get("quality_score", 0), reverse=True)
        best9 = sorted_photos[:9]
        while len(best9) < 9:
            best9.append(None)

        # 9宫格布局（C位=第5张放最佳）
        arranged = self._arrange_9grid(best9)

        # 生成朋友圈文案
        poi_names = list({c.get("poi_name", "") for c in day_checkins})
        weather = trip_info.get("weather", "晴")
        destination = trip_info.get("destination", "")

        caption = await self._generate_moment_caption(day, poi_names, destination, weather)

        return {
            "trip_id": trip_id,
            "type": "moment_9grid",
            "title": caption,
            "content": caption,
            "hashtags": self._gen_hashtags(destination, poi_names),
            "location_tag": poi_names[0] if poi_names else destination,
            "images": [{"url": p["url"], "caption": p.get("ai_caption", ""), "order": i + 1,
                        "is_cover": (i == 4)}
                       for i, p in enumerate(arranged) if p],
            "layout": "grid_9",
            "source_day": day,
            "source_poi": poi_names[0] if poi_names else "",
        }

    def _arrange_9grid(self, photos: list) -> list:
        """9宫格排列：C位(索引4)=最高分"""
        real = [p for p in photos if p]
        if len(real) < 2:
            return real
        real.sort(key=lambda p: p.get("quality_score", 0), reverse=True)
        result = [None] * 9
        result[4] = real[0]  # C位最佳
        positions = [0, 1, 2, 3, 5, 6, 7, 8]
        for i, p in enumerate(real[1:9]):
            if i < len(positions):
                result[positions[i]] = p
        return result

    async def _generate_moment_caption(self, day: int, poi_names: list, destination: str,
                                        weather: str) -> str:
        names_str = "→".join(poi_names[:3])
        prompt = f"""写一条朋友圈文案（40-80字，年轻化，带emoji）:
目的地: {destination} Day{day}
路线: {names_str}
天气: {weather}
要求: 轻松分享、不用太正式、像朋友在聊天"""

        try:
            return await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.9)
        except Exception:
            return f"📍{destination} Day{day}！{names_str}，今天太美了✨"

    # ========== 旅行卡片 ==========

    async def generate_travel_card(self, trip_id: str, day: int,
                                    day_checkins: list, trip_info: dict) -> dict:
        """生成旅行数据卡片"""
        all_photos = []
        for c in day_checkins:
            for p in (c.get("photos", []) or []):
                all_photos.append(p)

        best = max(all_photos, key=lambda p: p.get("quality_score", 0)) if all_photos else None

        poi_count = len(day_checkins)
        day_cost = sum(c.get("actual_cost", 0) or 0 for c in day_checkins)
        poi_names = [c.get("poi_name", "") for c in day_checkins]

        overlay = {
            "day": f"{day}/{trip_info.get('total_days', '?')}",
            "pois": poi_count,
            "poi_list": " → ".join(poi_names[:4]),
            "cost": f"¥{day_cost:.0f}",
            "weather": trip_info.get("weather", ""),
        }

        return {
            "trip_id": trip_id,
            "type": "day_summary",
            "title": f"Day {day} 打卡完成 ✓",
            "content": f"今日{poi_count}个打卡点，花费¥{day_cost:.0f}",
            "images": [{"url": best["url"], "order": 1, "is_cover": True}] if best else [],
            "layout": "single_v",
            "overlay_data": overlay,
            "source_day": day,
        }

    # ========== 精选合集 ==========

    async def generate_trip_highlight(self, trip_id: str, all_checkins: list,
                                       trip_info: dict) -> dict:
        """全程精选合集"""
        all_photos = []
        for c in all_checkins:
            for p in (c.get("photos", []) or []):
                all_photos.append({**p, "poi_name": c.get("poi_name", ""),
                                   "day": c.get("source_day", c.get("day", 1))})

        # 每天选最佳
        by_day: dict[int, list] = {}
        for p in all_photos:
            by_day.setdefault(p.get("day", 1), []).append(p)

        highlights = []
        for day in sorted(by_day.keys()):
            day_best = max(by_day[day], key=lambda p: p.get("quality_score", 0))
            highlights.append(day_best)

        destination = trip_info.get("destination", "")
        prompt = f"""写一段{destination}旅行的整体感悟（50-80字），作为旅行精选合集的开篇语。风格：温暖、治愈。"""
        try:
            caption = await self.llm.chat([{"role": "user", "content": prompt}], temperature=0.8)
        except Exception:
            caption = f"{destination}之旅，每一帧都值得珍藏。"

        return {
            "trip_id": trip_id,
            "type": "trip_highlight",
            "title": caption,
            "images": [{"url": p.get("url", ""), "caption": p.get("ai_caption", ""),
                        "order": i + 1, "is_cover": (i == 0)}
                       for i, p in enumerate(highlights[:12])],
            "layout": "card",
            "hashtags": self._gen_hashtags(destination, []),
            "location_tag": destination,
        }

    # ========== 花费总结卡 ==========

    async def generate_budget_card(self, trip_info: dict) -> dict:
        budget = trip_info.get("budget", {})
        return {
            "trip_id": trip_info.get("trip_id", ""),
            "type": "budget_card",
            "title": "💰 旅行花费总结",
            "content": f"总预算 ¥{budget.get('total', 0):.0f} → 实际 ¥{budget.get('actual_total', 0):.0f}",
            "images": [],
            "layout": "card",
            "overlay_data": budget,
        }

    # ================================================================
    #  Helpers
    # ================================================================

    def _gen_hashtags(self, destination: str, poi_names: list[str]) -> list[str]:
        tags = [f"#{destination}旅行"]
        for n in poi_names[:3]:
            tags.append(f"#{n}")
        tags.append("#旅行日记")
        return list(set(tags))[:8]

    @staticmethod
    def generate_share_code(length: int = 8) -> str:
        return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))
