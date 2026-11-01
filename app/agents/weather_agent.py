"""
天气适配智能体 — 和风天气 API + DeepSeek 行程调整建议
"""

from datetime import date as dt_date
from typing import Any

from app.agents.base import BaseAgent
from app.services.weather.qweather import qweather_service

_DEFAULT_SUGGESTIONS = [
    "关注当地天气预报，合理安排出行",
    "随身携带雨具，以防天气突变",
    "根据温度增减衣物，注意舒适度",
]


class WeatherAgent(BaseAgent):
    """天气适配智能体"""

    name = "weather"
    description = "高德天气 API 获取天气预报 → DeepSeek 生成行程调整建议"

    # ================================================================
    #  公共数据拉取（供 run 和 generate_impact_factors 复用）
    # ================================================================

    async def _fetch_forecasts(self, destination: str, start_date, end_date) -> list[dict]:
        """拉取天气预报，统一错误处理和日期解析"""
        if not qweather_service.api_key:
            print("  [WeatherAgent] AMAP_API_KEY 未配置，跳过天气查询")
            return []

        # 日期归一化
        sd = self._parse_date(start_date)
        ed = self._parse_date(end_date)
        if sd and ed and sd > ed:
            sd, ed = ed, sd  # 交换确保 start ≤ end

        try:
            return await qweather_service.get_forecast_for_dates(destination, sd or dt_date.today(), ed or dt_date.today())
        except Exception as e:
            print(f"  [WeatherAgent] 预报拉取失败: {e}")
            return []

    @staticmethod
    def _parse_date(value) -> dt_date | None:
        """安全解析日期，支持 str / date / None → dt_date"""
        if value is None:
            return None
        if isinstance(value, dt_date):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return dt_date.fromisoformat(value.strip())
            except (ValueError, TypeError):
                pass
        return None

    # ================================================================
    #  管线节点接口（确定性影响因子，不调 LLM）
    # ================================================================

    async def generate_impact_factors(
        self,
        destination: str,
        start_date,
        end_date,
        days: int,
        preferred_transport: str = "transit",
    ) -> dict[str, Any]:
        """
        Fetch weather forecasts and compute deterministic impact factors.

        Called by node_weather in the LangGraph pipeline.
        On API failure, returns neutral impacts (does not block pipeline).
        """
        from app.services.weather.impact import build_neutral_impacts, calculate_weather_impact

        parsed_start = self._parse_date(start_date) or dt_date.today()
        parsed_end = self._parse_date(end_date) or parsed_start
        if parsed_start > parsed_end:
            parsed_start, parsed_end = parsed_end, parsed_start

        forecasts = await self._fetch_forecasts(
            destination,
            parsed_start,
            parsed_end,
        )
        valid_forecasts = []
        for forecast in forecasts:
            forecast_date = self._parse_date(forecast.get("date"))
            if forecast_date is None:
                continue
            if parsed_start <= forecast_date <= parsed_end:
                valid_forecasts.append(forecast)

        neutral_impacts = build_neutral_impacts(
            days=days,
            start_date=parsed_start.isoformat(),
            preferred_transport=preferred_transport,
        )
        if not valid_forecasts:
            return {"forecasts": [], "impacts": neutral_impacts}

        real_impacts = calculate_weather_impact(
            valid_forecasts,
            preferred_transport=preferred_transport,
        )
        real_by_date = {
            impact.get("date"): impact
            for impact in real_impacts
            if impact.get("date")
        }
        merged_impacts = []
        for neutral in neutral_impacts:
            real = real_by_date.get(neutral["date"])
            if real:
                merged_impacts.append({
                    **neutral,
                    **real,
                    "date": neutral["date"],
                    "day_of_trip": neutral["day_of_trip"],
                })
            else:
                merged_impacts.append(neutral)

        return {"forecasts": valid_forecasts, "impacts": merged_impacts}

    # ================================================================
    #  BaseAgent 接口
    # ================================================================

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        destination = input_data.get("destination", "")
        start_date = input_data.get("start_date", "")
        end_date = input_data.get("end_date", "")
        daily_itinerary = input_data.get("daily_itinerary", [])

        # ---- 1. 拉取天气（current 独立 try，forecast 复用公共方法） ----
        current = None
        try:
            if qweather_service.api_key:
                current = await qweather_service.get_current_weather(destination)
        except Exception as e:
            print(f"  [WeatherAgent] 实时天气失败: {e}")

        forecasts = await self._fetch_forecasts(destination, start_date, end_date)

        if not forecasts:
            return {
                "weather_data": {"current": current, "forecasts": []},
                "suggestions": list(_DEFAULT_SUGGESTIONS),
                "status": "no_data",
            }

        # ---- 2. LLM 生成建议 ----
        suggestions = await self._generate_suggestions(destination, forecasts, daily_itinerary)
        if not suggestions:
            suggestions = list(_DEFAULT_SUGGESTIONS)

        return {
            "weather_data": {"current": current, "forecasts": forecasts},
            "suggestions": suggestions,
        }

    # ================================================================
    #  LLM 建议
    # ================================================================

    async def _generate_suggestions(self, dest: str, forecasts: list, itinerary: list) -> list:
        """DeepSeek 根据天气给出行建议"""
        fc_text = "\n".join(
            f"{f.get('date','?')} | 白天:{f.get('dayweather','')} | 夜间:{f.get('nightweather','')} | "
            f"{f.get('daytemp','')}~{f.get('nighttemp','')}°C | {f.get('daywind','')}风{f.get('daypower','')}级"
            for f in forecasts[:7]
        )

        trip_text = _build_trip_summary(itinerary)

        prompt = f"""{dest}旅行天气预报：
{fc_text}

行程：
{trip_text or '暂无行程'}

分析天气对行程的影响：
- 是否有雨天需要转移到室内景点？
- 温度是否适合户外活动？
- 给出1-3条具体的穿衣和出行建议

简洁回答，每条建议一行。"""

        try:
            resp = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.5)
            return [s.strip("- ") for s in resp.strip().split("\n") if s.strip()]
        except Exception:
            return []


# ================================================================
#  Helper
# ================================================================

def _build_trip_summary(itinerary: list) -> str:
    """安全构建行程摘要，防止 KeyError"""
    if not itinerary:
        return ""
    lines = []
    for day in itinerary:
        if not isinstance(day, dict):
            continue
        d = day.get("day", "?")
        names = [a.get("name", "?") for a in day.get("attractions", []) if isinstance(a, dict)]
        lines.append(f"第{d}天: {' → '.join(names)}")
    return "\n".join(lines)
