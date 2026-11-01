"""
Qwen-VL-Max Vision 模型适配器 — OpenAI 兼容接口

用于旅行照片 AI 标注、图片→偏好提取、封面选图等视觉任务。

图片传入方式：URL 优先，失败自动转 base64。
"""

import base64
import httpx
from pathlib import Path
from openai import AsyncOpenAI

from app.config import settings


class VisionLLM:
    """通义千问视觉模型 — 分析旅行照片内容"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
        self.model = "qwen-vl-max"

    # ================================================================
    #  图片加载（URL → base64 兜底）
    # ================================================================

    async def _load_image_data(self, image_url: str) -> str:
        """
        将图片 URL 转为 data URL（base64 编码）。
        如果 URL 已经是本地路径或 data URL，直接返回。
        Qwen-VL 从阿里云无法抓取外网 URL，需要 base64。
        """
        if image_url.startswith("data:"):
            return image_url
        # 本地文件
        if not image_url.startswith("http"):
            path = Path(image_url)
            if path.exists():
                suffix = path.suffix.lower().lstrip(".")
                mime = f"image/{suffix}" if suffix in ("jpg","jpeg","png","webp","gif") else "image/jpeg"
                data = path.read_bytes()
                b64 = base64.b64encode(data).decode("ascii")
                return f"data:{mime};base64,{b64}"
            return image_url
        # 远程 URL → 下载转 base64
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.get(image_url)
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "image/jpeg")
                    b64 = base64.b64encode(resp.content).decode("ascii")
                    return f"data:{ct};base64,{b64}"
        except Exception:
            pass
        # 兜底：直接用原始 URL（可能失败）
        return image_url

    # ================================================================
    #  单图分析
    # ================================================================

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """单张图片分析 — 返回自然语言描述"""
        img_data = await self._load_image_data(image_url)
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": img_data}},
                {"type": "text", "text": prompt},
            ],
        }]
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"  [Vision] 单图分析失败: {e}")
            return ""

    # ================================================================
    #  旅行照片标注
    # ================================================================

    async def caption_photo(
        self,
        image_url: str,
        poi_name: str = "",
        poi_type: str = "",
    ) -> dict:
        """
        为旅行照片生成 AI 描述 + 标签 + 场景判断。

        Returns:
            {"caption": "晨雾中断桥剪影...", "tags": ["晨雾","断桥","西湖"],
             "scene": "outdoor_water", "mood": "宁静", "has_people": False,
             "aesthetic_score": 4.5}
        """
        prompt = f"""你是一位旅行摄影师和内容创作者。请分析这张旅行照片。
{'拍摄地点: ' + poi_name if poi_name else ''}
{'地点类型: ' + poi_type if poi_type else ''}

请返回 JSON（不要 markdown 代码块，只返回纯 JSON）：
{{
  "caption": "一句中文描述（20-40字，文艺感，适合做相册配文）",
  "tags": ["标签1", "标签2", ...],    // 5-8个中文标签
  "scene": "indoor/outdoor_nature/outdoor_urban/outdoor_water/food/people",
  "mood": "宁静/热闹/浪漫/震撼/清新/温馨/神秘",
  "has_people": true/false,
  "aesthetic_score": 1-5             // 构图美感评分，5=杂志封面级别
}}"""

        import json
        try:
            text = await self.analyze_image(image_url, prompt, temperature=0.6, max_tokens=400)
            # 去 markdown 代码块
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            # 找第一个 {
            idx = text.find("{")
            if idx >= 0:
                text = text[idx:]
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  [Vision] 照片标注解析失败: {e}")
            return {
                "caption": f"在{poi_name}的美好时刻" if poi_name else "旅途中的精彩瞬间",
                "tags": ["旅行"] + ([poi_name] if poi_name else []),
                "scene": "outdoor_nature",
                "mood": "清新",
                "has_people": False,
                "aesthetic_score": 4.0,
            }

    # ================================================================
    #  多图分析 — 提取旅行偏好
    # ================================================================

    async def extract_preferences(self, image_urls: list[str], user_message: str = "") -> dict:
        """
        从多张照片 + 用户文字提取旅行偏好和目的地线索。

        Returns:
            {"destination_hint": "川西/云南", "preferences": ["自然风光","户外徒步"],
             "pace": "适中", "vibe": "冒险/休闲/浪漫/文艺"}
        """
        content = [{"type": "text", "text": "请依次仔细看以下图片，然后回答。"}]
        for url in image_urls[:5]:  # 最多 5 张
            img_data = await self._load_image_data(url)
            content.append({"type": "image_url", "image_url": {"url": img_data}})
        content.append({
            "type": "text",
            "text": f"""以上是用户收藏或拍摄的旅行照片。用户说: "{user_message or '想去这样的地方'}"

请分析这些照片的共性，返回 JSON（不要 markdown 代码块，只返回纯 JSON）：
{{
  "destination_hint": "推测的目的地或地区（如 川西、日本京都、云南大理 等）",
  "scene_summary": "这些照片的共同特点（20字以内）",
  "preferences": ["标签1", "标签2", ...],  // 从照片推测的旅行偏好
  "pace": "紧凑/适中/轻松",
  "vibe": "冒险/休闲/浪漫/文艺/美食/亲子"
}}"""
        })

        import json
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                temperature=0.5,
                max_tokens=500,
            )
            text = resp.choices[0].message.content or ""
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            idx = text.find("{")
            if idx >= 0:
                text = text[idx:]
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  [Vision] 偏好提取失败: {e}")
            return {
                "destination_hint": "",
                "scene_summary": "",
                "preferences": [],
                "pace": "适中",
                "vibe": "休闲",
            }

    # ================================================================
    #  封面选图 — 批量评分
    # ================================================================

    async def score_photos(self, image_urls: list[str]) -> list[dict]:
        """
        对一批照片打分，选最佳封面。

        Returns: [{"url": "...", "score": 4.5, "reason": "..."}, ...]
        """
        results = []
        for url in image_urls[:10]:  # 每次最多 10 张
            prompt = """评价这张旅行照片作为游记封面的合适度（1-5 分）。
考虑：构图、光线、是否有故事感、是否适合做开篇。

只返回 JSON：{"score": 4.5, "reason": "一句话理由（10字以内）"}"""
            import json
            try:
                text = await self.analyze_image(url, prompt, temperature=0.3, max_tokens=100)
                text = text.strip()
                idx = text.find("{")
                if idx >= 0:
                    text = text[idx:]
                result = json.loads(text)
                results.append({"url": url, **result})
            except Exception:
                results.append({"url": url, "score": 3.0, "reason": "默认"})

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results


# 单例
vision_llm = VisionLLM()
