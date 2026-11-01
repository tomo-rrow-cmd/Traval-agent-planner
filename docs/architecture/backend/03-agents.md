# Agent 系统

## 1. 基类

实现位置：`app/agents/base.py`

```python
class BaseAgent(ABC):
    name: str           # 唯一标识
    description: str    # 说明
    llm: BaseLLM        # LLM 实例
    tools: list[dict]   # 注册的工具定义

    async def call_llm(messages, temperature) -> str              # 调 LLM (3次重试)
    async def call_llm_with_tools(messages, temperature) -> dict  # Function Calling
    def register_tool(tool_def)                                   # 手动注册工具
    def register_tools_from_registry(names)                       # 从全局表注册
    def validate_output(data, SchemaClass) -> dict                # Pydantic 校验
```

## 2. 工具系统

实现位置：`app/agents/tools/tool_registry.py`

```python
# 注册工具
register("tool_name", "description", {parameters_schema}, handler_function)

# 已注册工具分组：
# ┌─────────────────┬────────────────┬──────────────────────────┐
# │ 工具名           │ 数据来源        │ 用途                     │
# ├─────────────────┼────────────────┼──────────────────────────┤
# │ search_attractions │ Chroma RAG     │ 景点语义搜索             │
# │ search_restaurants │ Chroma RAG     │ 餐厅语义搜索             │
# │ search_hotels      │ Chroma RAG     │ 酒店语义搜索             │
# │ get_weather        │ 高德天气 API    │ 天气查询                 │
# │ get_route          │ 高德 direction  │ 路径规划                 │
# │ meituan_travel     │ mttravel CLI   │ 酒店/景点/行程 (真实价格) │
# │ railway_search_*   │ 12306 爬虫      │ 火车票余票/票价          │
# └─────────────────┴────────────────┴──────────────────────────┘
```

## 3. 编排管线

```text
UserInteractionAgent
  ├─ daily_chat / collecting / awaiting_confirmation → waiting_input
  └─ travel_planning + ready + confirmed
       → [并行] AttractionAgent + FoodAgent + HotelAgent
       → DecisionAgent.run_round1
       → DetailAgent
       → DecisionAgent.run_round2
       → TrafficAgent
       → BudgetAgent
       ├─ should_retry=true → adjust → 从并行阶段重跑
       └─ should_retry=false → END
```

当前主图定义在 `app/orchestrator/graph.py`，包含 8 个节点（parallel_planning → decision_r1
→ detail_enrich → decision_r2 → plan_traffic → budget → adjust → 回到 parallel_planning）。

主图之外的 Agent：
- **WeatherAgent**、**RouteOptimizerAgent**、**SouvenirAgent** — 仍在仓库中，但没有挂入当前 `planner_graph`，文档和产品展示不得把它们描述为每次规划必经阶段。
- **TripAgent** — 行程执行状态管理（签到/进度/提醒/预算追踪），独立调用，不经过 LangGraph。
- **TravelogueAgent** — 游记生成 + 照片整理 + 社交素材，独立调用，不经过 LangGraph。
- **AdjustAgent** — 天气/时间/预算/用户主动调整，主编排图中通过 `node_adjust_params` 触发其参数修正逻辑，全场景流程为预留能力。

## 4. Agent 输入输出规范

详见 `app/schemas/agent_outputs.py`，每个 Agent 的输出经过 Pydantic 校验。

### UserInteractionAgent

```json
入: {"message": "我从武汉出发去北京3天", "history": [...], "context": {}}
出: {"reply": "请确认规划参数", "mode": "travel_planning", "status": "awaiting_confirmation",
     "extracted": {"destination":"北京","origin":"武汉",...}, "ready": false, "confirmed": false}
```

### AttractionAgent

```json
入: {"destination": "北京", "days": 3, "preferences": ["历史"], "pace": "适中"}
出: {
  "daily_plan": [
    {"day": 1, "attractions": [
      {"name": "故宫博物院", "reason": "...", "duration_hours": 3.5,
       "latitude": 39.918, "longitude": 116.397, "address": "..."}
    ]}
  ],
  "candidate_count": 25
}
```

### FoodAgent

```json
入: {"destination": "北京", "days": 3, "cuisine_preferences": ["川菜"], "meal_budget": 100}
出: {
  "meal_plan": [
    {"day": 1, "meals": [
      {"meal": "午餐", "restaurant": "河沿肉饼", "reason": "...", "avg_price": 69}
    ]}
  ]
}
```

### HotelAgent

```json
入: {"destination": "北京", "days": 3, "hotel_star_min": 3, "budget_per_night": 500}
出: {
  "meituan_raw": "美团Markdown完整结果 (真实价格+评分+图片)",
  "hotel_plan": {
    "recommendations": [
      {"name": "汉庭前门店", "reason": "...", "price_per_night": 259,
       "price_verified": true, "nights": 2, "total": 518}
    ]
  },
  "source": "meituan"
}
```

### TrafficAgent

```json
入: {"origin": "武汉", "destination": "北京", "days": 3,
     "daily_locations": [...], "hotel_plan": {...}, "preferred_transport": "地铁"}
出: {
  "daily_traffic": [
    {"day": 1, "segments": [
      {"from": "天安门", "to": "故宫", "distance_km": 1.2, "time_min": 15, "cost": 3}
    ], "total_time_min": 15, "total_cost": 3}
  ],
  "total_traffic_cost": 31,
  "big_traffic": {"trains": [{"trainCode": "G66", "prices": {"二等座": "520.5"}}]}
}
```

### BudgetAgent

```json
入: {"total_budget": 10000, "days": 3, "travelers": 1, "expenses": {...}}
出: {
  "total_budget": 10000, "actual_total": 1642, "remaining": 8358,
  "actual_details": [{"category": "住宿", "budget": 3500, "spent": 518, "status": "ok"}],
  "warnings": []
}
```

### DecisionAgent

两轮确定性决策（不走 LLM），实现位置：`app/agents/decision_agent.py`

**Round 1（定稿景点 + 餐厅）：**

```json
入: {"daily_plan": [...], "meal_plan": [...]}
出: {
  "stage": "finalized_r1",
  "daily_plan": [{"day": 1, "attractions": [...≤4], "meals": [...]}],
  "decision_needed": false, "auto_trimmed": false
}
```

**Round 2（通勤评分选酒店）：**

```json
入: {"hotel_plan": {...}, "daily_plan": [...], "destination": "北京"}
出: {
  "hotel_plan": {
    "recommendations": [...],
    "selected": "汉庭前门店",
    "selected_hotel": {"name": "汉庭前门店", "commute_score": 8.5, ...},
    "selection_reason": "交通评分 8.5 最优"
  }
}
```

### DetailAgent

定稿后深度扩展，实现位置：`app/agents/detail_agent.py`

```json
入: {"daily_plan": [...], "meal_plan": [...], "destination": "北京"}
出: {
  "attraction_details": [{"name": "故宫", "tips": [...], "famous_spots": [...]}],
  "food_details": [{"name": "胡大饭馆", "signature_dishes": [...], "user_feedback": [...]}]
}
```

挑选阈值：景点评分 ≥ 4.3、餐厅评分 ≥ 4.2，各最多扩展 3 个。数据源为美团 CLI（60s 超时）→ 高德 POI 兜底；无真实数据则跳过不编造。

### AdjustAgent

动态调整，实现位置：`app/agents/adjust_agent.py`

```json
入: {"trigger_type": "weather|time_drift|budget_alert|user_request", ...}
出: {
  "trigger_type": "budget_alert",
  "trigger_detail": {"spent": 12000, "total": 10000, "over_pct": 20.0},
  "suggestions": [{"action": "降级餐饮", "detail": "晚餐选人均¥50以下"}],
  "reason": "已花 ¥12000/10000 (20.0%)，剩余2天建议控制花费"
}
```

主编排图中通过 `node_adjust_params` 触发参数修正（`hotel_budget ≥ 200`、`meal_budget ≥ 50` 硬地板，`hotel_star` 直降 2 星）。天气/时间/用户主动调整场景的完整流程为预留能力。

### TripAgent

行程执行状态管理，实现位置：`app/agents/trip_agent.py`（独立调用，不经过 LangGraph）

```json
入: {"action": "start|checkin|reminder|progress", ...}
出 (start): {
  "total_pois": 18, "total_days": 3,
  "days_outline": [{"day": 1, "stops": [...]}],
  "budget_total": 10000
}
出 (checkin): {
  "time_delta_min": 15, "on_time": true,
  "trigger_adjustment": false
}
出 (reminder): {
  "day": 2, "reminder_text": "明天是第2天...",
  "first_stop": "故宫", "first_stop_time": "08:00",
  "weather_advice": "气温28°C，建议短袖+防晒"
}
出 (progress): {
  "poi_progress_pct": 33.3, "day_progress_pct": 66.7,
  "overall_progress_pct": 50.0, "status": "on_track"
}
```

### TravelogueAgent

游记生成 + 社交素材，实现位置：`app/agents/travelogue_agent.py`（独立调用，不经过 LangGraph）

```json
入: {"action": "generate|photo_annotate|social_post", ...}
出 (generate): {
  "travelogue": {
    "title": "北京3日文化之旅",
    "content": "## Day 1...",
    "style": "日记风",
    "word_count": 1200
  }
}
```

### WeatherAgent

```json
入: {"destination": "北京", "start_date": "2026-07-10", "end_date": "2026-07-12"}
出: {
  "weather_data": {"current": {"temp":"28","text":"多云"}, "forecasts": [...]},
  "suggestions": ["夜间有雷阵雨，建议下午4点后安排室内景点"]
}
```
