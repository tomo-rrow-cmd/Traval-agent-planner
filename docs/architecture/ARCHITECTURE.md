# AI 旅行规划师 — 后端架构文档

> 供团队协作参考，覆盖架构、数据库、RAG、Agent、API 全链路。
> 当前实现基线以 `.agent/decisions.md`、`.agent/conventions.md` 和 `docs/api/API接口规范文档.md` 为准；
> 本文件为可读性架构概览，与上述文档冲突时以后者为准。

---

## 一、整体架构（七层）

```
客户端 (Web Vue 3 / Android Kotlin)
    │ HTTP + SSE
    ▼
┌─ 接入层 ──────────────────────────────────────────┐
│  Nginx / API Gateway / JWT 鉴权 / 限流 / 日志      │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ API 层 (FastAPI) ────────────────────────────────┐
│  app/api/router.py         总路由                  │
│  app/api/v1/auth.py        认证接口 (契约 MVP)      │
│  app/api/v1/chat.py        对话 & SSE 消息接口       │
│  app/api/v1/plan.py        方案生成/导出/分享接口    │
│  app/api/v1/trip.py        行程执行 & 签到接口       │
│  app/api/v1/travelogue.py  游记生成 & 分享接口       │
│  app/api/v1/user.py        用户资料 & 偏好接口       │
│  app/api/v1/data.py        基础数据查询接口          │
│  app/api/v1/ops.py         健康检查 & 任务状态       │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 业务应用服务层 ──────────────────────────────────┐
│  app/services/application/conversation_service.py  │
│  app/services/application/plan_service.py          │
│  app/services/application/trip_service.py          │
│  app/services/application/travelogue_service.py    │
│  app/services/application/user_service.py          │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 编排层 (LangGraph) ───────────────────────────────┐
│  app/orchestrator/pipeline.py  编排管线入口         │
│  app/orchestrator/graph.py     LangGraph 工作流图   │
│  app/orchestrator/nodes.py     编排节点实现         │
│  app/orchestrator/state.py     PlannerState 状态    │
│  app/orchestrator/conflict_detection.py 冲突检测    │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 智能体层 — 主编排 Agent + 独立调用 Agent ─────────┐
│  app/agents/base.py            基类 (LLM/重试/工具) │
│  app/agents/user_interaction_agent.py  对话入口     │
│  app/agents/attraction_agent.py       景点规划      │
│  app/agents/food_agent.py             美食推荐      │
│  app/agents/hotel_agent.py            住宿推荐      │
│  app/agents/decision_agent.py         两轮定稿决策  │
│  app/agents/detail_agent.py           详情扩展补全  │
│  app/agents/traffic_agent.py          交通规划      │
│  app/agents/budget_agent.py           预算核算      │
│  app/agents/adjust_agent.py           超预算参数修正│
│  app/agents/trip_agent.py            行程执行      │
│  app/agents/travelogue_agent.py      游记生成      │
│  app/agents/weather_agent.py         天气查询建议  │
│  app/agents/route_optimizer_agent.py 路线优化      │
│  app/agents/souvenir_agent.py        纪念品推荐    │
│  app/agents/photo_planner_agent.py   拍照规划      │
│  app/agents/tools/                   工具注册表    │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 服务能力层 ──────────────────────────────────────┐
│  app/services/llm/          LLM (DeepSeek/豆包/千问)│
│  app/services/map/          高德地图 (POI/路径)      │
│  app/services/weather/      高德天气 + 影响因子计算  │
│  app/services/vector/       BGE-M3 + Chroma + Reranker│
│  app/services/third_party/  美团酒旅 CLI / 12306     │
│  app/services/export/       Markdown/PDF/PNG/DOCX    │
│  app/services/data/         基础数据服务层           │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 数据存储层 ──────────────────────────────────────┐
│  PostgreSQL    业务数据 (users, conversations,      │
│                messages, conversation_plan_runs,     │
│                plans, attractions, restaurants,      │
│                hotels, trips, travelogues 等)        │
│  Chroma        向量库 (attractions/restaurants/      │
│                hotels 三个 collection)               │
│  Redis         缓存/会话/锁 (配置预留)               │
└────────────────────────────────────────────────────┘
```

**依赖方向**：`API → 应用服务层 → 编排层 → 智能体层 → 服务能力层 → 数据存储层`（严禁反向依赖）

---

## 二、数据库设计

### 2.1 PostgreSQL — 核心业务表

| 表名 | 对应 Model | 用途 |
|------|-----------|------|
| `users` | `app/db/models/user.py` | 用户账户、密码哈希、偏好 |
| `conversations` | `app/db/models/conversation.py` | 对话会话，含标题、状态、置顶、最近方案引用 |
| `messages` | `app/db/models/conversation.py` | 对话消息，支持 sequence 排序和 client_message_id 幂等 |
| `conversation_plan_runs` | `app/db/models/conversation.py` | 同一会话内多次方案生成的摘要记录 |
| `plans` | `app/db/models/plan.py` | 长期可编辑/分享/收藏的正式方案 |
| `attractions` | `app/db/models/attraction.py` | 景点基础数据（POI） |
| `restaurants` | `app/db/models/restaurant.py` | 餐厅基础数据（POI） |
| `hotels` | `app/db/models/hotel.py` | 酒店基础数据（POI） |
| `trips` | `app/db/models/trip.py` | 行程执行记录（签到、预算追踪） |
| `travelogues` | `app/db/models/travelogue.py` | 游记内容、素材与分享 |

### 2.2 迁移管理

```
app/db/migrations/
├── env.py             # Alembic 环境配置
├── script.py.mako     # 迁移脚本模板
└── versions/          # 迁移历史文件
```

- 生成迁移：`alembic revision --autogenerate -m "描述"`
- 执行迁移：`alembic upgrade head`
- 当前迁移基线版本：`20260717_02`

### 2.3 关键设计决策

- 消息序列号通过行级锁 `SELECT ... FOR UPDATE` 分配，辅以数据库唯一约束保证并发安全。
- 消息幂等通过 `client_message_id` 唯一约束实现。
- 分页同时支持页码分页（`page`/`page_size`）和双向游标（`before_id`/`after_id`）。
- `conversation_plan_runs` 只保存方案摘要供会话上下文使用；长期方案由 `plans` 表承载。
- 数据库持久化时间字段使用 UTC 存储，API 日期时间使用 ISO 8601 格式并带时区。
- 重要业务表预留 `extra`/`metadata` JSONB 字段，但不得用 JSONB 替代核心可查询字段。

---

## 三、RAG 系统

### 3.1 架构

```
用户查询 "北京历史人文景点适合亲子"
    │
    ▼
EmbeddingService (BAAI/bge-m3, 1024维)
    │
    ▼
Chroma VectorStore (Top-K 召回)
    │
    ├── attractions  collection
    ├── restaurants  collection
    └── hotels       collection
    │
    ▼
BGE Reranker (BAAI/bge-reranker-base) 重排 → 最终 K 条
    │
    ▼
LLM → 排序/筛选/写推荐理由 → 最终结果
```

### 3.2 检索入口

统一通过 `app/services/vector/rag.py` 的 `rag_search` 进入：
`embedding → Chroma Top-K 召回 → reranker 重排 → final K`

Agent 和工具注册表不得重复手写 Chroma 结果解析逻辑。

### 3.3 降级策略

- BGE 模型未缓存、Chroma 无数据时返回可解释降级结果。
- 默认离线测试不依赖真实模型下载和向量库数据。
- 从旧 512 维模型切换需重建 `chroma_data/` collection。

---

## 四、Agent 系统

### 4.1 基类 (`app/agents/base.py`)

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

### 4.2 工具系统 (`app/agents/tools/tool_registry.py`)

```python
# 注册工具
register("tool_name", "description", {parameters_schema}, handler_function)
```

可用工具：

| 工具名 | 数据来源 | 用途 |
|--------|---------|------|
| `search_attractions` | Chroma RAG | 景点语义搜索 |
| `search_restaurants` | Chroma RAG | 餐厅语义搜索 |
| `search_hotels` | Chroma RAG | 酒店语义搜索 |
| `get_weather` | 高德天气 API | 天气查询 |
| `get_route` | 高德 direction API | 路径规划 |
| `meituan_travel` | mttravel CLI | 酒店/景点/行程 (真实价格) |
| `railway_search_*` | 12306 查询 | 火车票余票/票价 |

### 4.3 主编排管线

```
UserInteractionAgent 对话 → 提取 {destination, origin, days, budget, preferences, ...}
    │
    ▼ 用户确认 (confirmed=true, ready=true)
    │
    ┌──────────────────────────────────────────────────────┐
    │ [并行]  AttractionAgent + FoodAgent + HotelAgent      │
    │   ↓                                                   │
    │ DecisionAgent R1（定稿景点和餐厅，每日 ≤4 景点）       │
    │   ↓                                                   │
    │ DetailAgent（补充重点景点和餐厅详情，美团/高德）       │
    │   ↓                                                   │
    │ DecisionAgent R2（按通勤评分选择最优酒店）             │
    │   ↓                                                   │
    │ TrafficAgent（大交通 12306 + 市内路线高德）            │
    │   ↓                                                   │
    │ BudgetAgent（预算核算 + 最终方案）                     │
    │   ├─ 未超预算 → 输出 final_plan                        │
    │   └─ 超预算（≤30% 且 retry<2）→ AdjustAgent           │
    │       → 回到并行阶段重跑（最多 2 次）                  │
    └──────────────────────────────────────────────────────┘
```

### 4.4 独立调用 Agent（不经过 LangGraph）

| Agent | 用途 | 调用方 |
|-------|------|--------|
| TripAgent | 行程执行：签到、进度、每日提醒、预算追踪 | `app/api/v1/trip.py` |
| TravelogueAgent | 游记生成、照片整理、社交素材 | `app/api/v1/travelogue.py` |
| WeatherAgent | 天气查询与出行建议 | 独立服务调用 |
| RouteOptimizerAgent | TSP/VRP 路径优化 | 独立工具模块 |
| SouvenirAgent | 纪念品推荐 | 独立 Agent |
| PhotoPlannerAgent | 拍照规划建议 | 独立 Agent |

### 4.5 编排约束

- Agent 必须通过 `BaseAgent` 接入编排层，不允许绕过 LangGraph 直接互相调用。
- Agent 之间通过 `PlannerState`（`app/orchestrator/state.py`）共享状态。
- 每个编排节点只能写入自己负责的 State 字段。
- Agent 输出写入 State 前必须经过 Pydantic Schema 校验（`app/schemas/agent_outputs.py`）。
- 规划进度通过 LangGraph 节点更新转为 SSE `progress` 事件。
- LLM 调用统一经过 `app/services/llm/` 服务层；当前主模型为 DeepSeek，豆包和通义千问保留为备选适配器。
- 对话 Agent 必须先识别 `daily_chat` 与 `travel_planning`，收齐参数后进入 `awaiting_confirmation`，用户明确确认后才启动完整规划。

---

## 五、API 接口规范

### 5.1 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... },
  "request_id": "req_abc123"
}
```

业务错误码与 HTTP status 分离：

| 场景 | HTTP Status | 业务码 |
|------|------------|--------|
| 请求参数校验错误 | 400 | 10001 |
| 未授权 | 401 | 20001 |
| 资源不存在 | 404 | 10003 |
| 导出格式不支持 | 400 | 40006 |

分页响应统一使用 `list`/`total`/`page`/`page_size`/`total_pages`。

### 5.2 公开路径概览

| 领域 | 路径 |
|------|------|
| 认证 | `POST /api/v1/auth/register`、`POST /api/v1/auth/sms-codes`、`POST /api/v1/auth/sessions`、`POST /api/v1/auth/tokens`、`DELETE /api/v1/auth/sessions/current` |
| 用户 | `GET/PUT /api/v1/user/profile`、`GET/PUT /api/v1/user/preferences`、`POST /api/v1/user/sessions/anonymous/merge` |
| 对话 | `POST/GET /api/v1/chat/sessions`、`DELETE /api/v1/chat/sessions/{sessionId}`、`POST/GET /api/v1/chat/sessions/{sessionId}/messages`、`GET /api/v1/chat/sessions/{sessionId}/stream`、`GET /api/v1/chat/sessions/{sessionId}/plans` |
| 方案 | `GET/POST /api/v1/plans`、`GET/PATCH/DELETE /api/v1/plans/{planId}`、`POST /api/v1/plans/{planId}/generations`、`POST /api/v1/plans/{planId}/exports`、`POST /api/v1/plans/{planId}/shares`、`POST /api/v1/plans/{planId}/favorites` |
| 行程 | `GET/POST /api/v1/trips`、`GET/PATCH /api/v1/trips/{tripId}`、`GET /api/v1/trips/{tripId}/progress`、`POST/GET /api/v1/trips/{tripId}/checkins`、`POST/GET /api/v1/trips/{tripId}/expenses`、`POST/GET /api/v1/trips/{tripId}/adjustments` |
| 游记 | `GET/POST /api/v1/travelogues`、`GET/PATCH /api/v1/travelogues/{id}`、`POST /api/v1/travelogues/{id}/publish`、`POST/GET /api/v1/travelogues/materials`、`POST /api/v1/travelogues/shares`、`GET /api/v1/travelogues/shares/{shareCode}` |
| 基础数据 | `GET /api/v1/data/cities`、`GET /api/v1/data/attractions`、`GET /api/v1/data/attractions/{id}`、`GET /api/v1/data/restaurants`、`GET /api/v1/data/hotels`、`GET /api/v1/data/weather` |
| 运维 | `GET /api/v1/health`、`GET /api/v1/tasks/{taskId}`、`GET /api/v1/tasks/{taskId}/download` |

### 5.3 SSE 事件类型

规划 SSE 接口包括 `POST /chat/sessions/{sessionId}/messages`、`GET /chat/sessions/{sessionId}/stream`、`POST /plans`、`PATCH /plans/{planId}`、`POST /plans/{planId}/generations`。

| 事件类型 | 说明 | 典型 payload |
|----------|------|-------------|
| `message_delta` | 对话回复增量片段 | `{"role": "assistant", "content_delta": "...", "sequence": 1}` |
| `message` | 完整消息（持久化后兜底） | `{"role": "assistant", "content": "...", "sequence": 1}` |
| `step_start` | 编排步骤开始 | `{"stage": "attractions"}` |
| `progress` | 进度更新 | `{"stage": "attractions", "progress": 0.3}` |
| `step_end` | 编排步骤结束 | `{"stage": "attractions"}` |
| `done` | 全流程完成 | `{"plan_run_id": "...", "session_id": "...", "summary": {...}}` |
| `error` | 错误信息 | `{"code": 50000, "message": "..."}` |

### 5.4 关键 API 约束

- 方案生成必须有显式确认门控：`POST /plans` 和 `POST /plans/{planId}/generations` 请求体使用 `confirmed` 字段。
- 未确认时只返回等待确认的 SSE 消息，不进入 LangGraph 规划。
- 对话 Agent 在 `mode=travel_planning`、`ready=true` 且 `confirmed=true` 时才启动完整规划。
- 导出：Markdown 同步返回；PDF/PNG/DOCX 创建临时任务，通过 `GET /tasks/{taskId}` 查询、`GET /tasks/{taskId}/download` 下载。产物保留 1 小时。
- 错误响应不得暴露堆栈、SQL、密钥或第三方原始错误。

---

## 六、第三方服务

| 服务 | Key 位置 | 用途 | 状态 |
|------|----------|------|------|
| DeepSeek | `.env` → `DEEPSEEK_API_KEY` | 主 LLM | ✅ 已接入 |
| 高德地图 | `.env` → `AMAP_API_KEY` | POI/路径/天气 | ✅ 已接入 |
| 美团酒旅 | `~/.config/meituan-travel/config.json` (由 `.env` `MEITUAN_TOKEN` 同步) | 酒店/景点/行程真实价格 | ✅ 已接入 |
| 12306 | 无需 Key | 火车票查询 | ✅ 已接入 |
| 豆包 | `.env` → `DOUBAO_API_KEY` | 备选 LLM | 预留 |
| 通义千问 | `.env` → `QWEN_API_KEY` | 备选 LLM | 预留 |
| Chroma | 本地 `chroma_data/` | 向量检索 | ✅ 已接入 |
| BGE-M3 | ModelScope 下载/缓存 | Embedding (1024维) | ✅ 已接入 |
| BGE-Reranker | ModelScope 下载/缓存 | 候选重排 | ✅ 已接入 |
| PostgreSQL | `.env` → `DATABASE_URL` | 业务数据存储 | ✅ 已接入 |
| Redis | `.env` → `REDIS_URL` | 缓存/会话 | 配置预留 |

所有第三方调用必须通过适配器或服务接口封装；失败时最多自动重试 3 次，重试失败后返回可解释降级结果。

---

## 七、关键文件索引

```
项目根/
├── app/
│   ├── agents/             智能体层 (16 Agent)
│   │   ├── base.py             基类 (LLM / 重试 / 工具)
│   │   ├── tools/tool_registry.py  全局工具注册表
│   │   ├── user_interaction_agent.py
│   │   ├── attraction_agent.py
│   │   ├── food_agent.py
│   │   ├── hotel_agent.py
│   │   ├── decision_agent.py
│   │   ├── detail_agent.py
│   │   ├── traffic_agent.py
│   │   ├── budget_agent.py
│   │   ├── adjust_agent.py
│   │   ├── trip_agent.py
│   │   ├── travelogue_agent.py
│   │   ├── weather_agent.py
│   │   ├── route_optimizer_agent.py
│   │   ├── souvenir_agent.py
│   │   ├── photo_planner_agent.py
│   │   └── context.py
│   │
│   ├── api/                接口层
│   │   ├── router.py           总路由注册
│   │   └── v1/{auth,chat,data,ops,plan,travelogue,trip,user}.py
│   │
│   ├── orchestrator/       编排层
│   │   ├── pipeline.py         编排管线入口
│   │   ├── graph.py            LangGraph 工作流图
│   │   ├── nodes.py            编排节点实现
│   │   ├── state.py            PlannerState 状态定义
│   │   └── conflict_detection.py  冲突检测
│   │
│   ├── schemas/            数据模型
│   │   ├── common.py           统一响应
│   │   ├── agent_outputs.py    Agent 输出 Schema
│   │   ├── chat.py / plan.py / user.py / data.py / trip.py / travelogue.py
│   │
│   ├── services/           服务层
│   │   ├── application/       业务应用服务 (conversation, plan, trip, travelogue, user)
│   │   ├── llm/{base,deepseek,doubao,qwen,prompt_manager,vision}.py
│   │   ├── map/{amap,geocode}.py
│   │   ├── weather/{qweather,impact}.py
│   │   ├── vector/{embedding,vector_store,rag,reranker,scorer,poi_index}.py
│   │   ├── third_party/{meituan,meituan_parser,railway12306,poi_live}.py
│   │   ├── export/{exporter,task_manager}.py
│   │   └── data/{attraction,restaurant,hotel}_service.py
│   │
│   ├── db/                 数据层
│   │   ├── session.py         数据库会话管理
│   │   ├── models/            ORM 模型 (8+ 表)
│   │   ├── repositories/      DAO 层
│   │   └── migrations/        Alembic 迁移
│   │
│   ├── core/               安全能力
│   │   └── security.py         JWT / 密码哈希
│   │
│   └── utils/              工具
│       ├── validator.py       预算下限门禁等
│       └── ...
│
├── scripts/
│   ├── start_backend.sh / .ps1 / .cmd   后端启动脚本
│   ├── start_frontend.sh                前端启动脚本
│   ├── seed_poi.py                      POI 数据拉取
│   └── ...
│
├── tests/
│   ├── test_api.py         API 契约测试
│   ├── test_agents.py      Agent 测试
│   └── ...
│
├── .agent/                架构约束、编码规范、决策记录、禁飞区
├── .env.example           环境变量示例
├── requirements.txt        Python 依赖
├── main.py                项目启动入口
└── README.md              项目说明
```

---

## 八、扩展指南

### 新增 Agent
1. 继承 `BaseAgent`，实现 `run(input_data) -> dict`
2. 在 `app/schemas/agent_outputs.py` 添加输出 Schema
3. 在 `app/orchestrator/nodes.py` 添加编排节点
4. 在 `app/orchestrator/graph.py` 注册节点 + 边
5. 在编排管线中接入调用

### 新增工具
1. 在 `app/agents/tools/tool_registry.py` 写 handler 函数 + `register()`
2. 在 Agent `__init__` 中 `register_tools_from_registry(["name"])`

### 新增数据源
1. 在 `app/services/third_party/` 新建适配器
2. 在 `tool_registry.py` 注册为工具
3. Agent 通过工具调用新数据源

### 新增 API 接口
1. 在 `app/schemas/` 定义 Request/Response Schema
2. 在 `app/api/v1/` 新建或扩展路由文件
3. 在 `app/api/router.py` 注册路由
4. 使用统一响应格式 `{ code, message, data, request_id }`

### 新增数据库表
1. 在 `app/db/models/` 新增 ORM Model
2. 生成 Alembic 迁移：`alembic revision --autogenerate -m "描述"`
3. 在 `app/db/repositories/` 新增 DAO
4. 同步更新 `docs/architecture/database/数据库设计文档.md`
