# 后端代码说明文档

> 面向逐行讲解的代码导读，覆盖后端全部核心模块。建议按目录从上到下阅读。

---

## 目录

1. [项目概览](#1-项目概览)
2. [请求全流程：从 HTTP 到 SSE 响应](#2-请求全流程从-http-到-sse-响应)
3. [入口与配置层](#3-入口与配置层)
4. [API 层 — 路由与依赖注入](#4-api-层--路由与依赖注入)
5. [编排层 — LangGraph 五阶段管线](#5-编排层--langgraph-五阶段管线)
6. [Agent 层 — 智能体体系](#6-agent-层--智能体体系)
7. [工具系统 — Function Calling](#7-工具系统--function-calling)
8. [服务层 — LLM / RAG / 地图 / 第三方](#8-服务层--llm--rag--地图--第三方)
9. [数据层 — ORM / Repository / 迁移](#9-数据层--orm--repository--迁移)
10. [Schema 层 — Pydantic 校验体系](#10-schema-层--pydantic-校验体系)
11. [SSE 流式架构](#11-sse-流式架构)
12. [异常与错误处理](#12-异常与错误处理)
13. [讲解建议 — 推荐逐行讲解的文件](#13-讲解建议--推荐逐行讲解的文件)

---

## 1. 项目概览

### 1.1 这是什么项目

AI Travel Planner 是一个**多智能体协作的 AI 旅行规划系统**。用户通过自然语言对话描述旅行需求，系统经过"意图识别 → 参数提取 → 五阶段并行规划 → 决策定稿 → 预算核算"的完整流程，生成一份结构化的 Day-by-Day 旅行方案。

### 1.2 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Web 框架 | **FastAPI** 0.115 | HTTP API + SSE 流 |
| ASGI | **Uvicorn** | 异步服务器 |
| ORM | **SQLAlchemy 2.0** (async) | 数据库操作 |
| 数据库 | **PostgreSQL** + asyncpg | 业务数据存储 |
| 向量库 | **ChromaDB** | RAG 语义检索 |
| 缓存 | **Redis** | 预留 |
| 多智能体编排 | **LangGraph** 0.2 | DAG 工作流 |
| LLM | **DeepSeek** (OpenAI 兼容) | 主模型 |
| Embedding | **BGE-M3** (1024维) | 文本向量化 |
| Reranker | **BGE-reranker-base** | 召回重排 |
| 地图 | **高德 Web API** | POI 搜索 / 路径规划 / 天气 |
| 第三方 | 美团酒旅 CLI / 12306 爬虫 | 实时酒店价格 / 火车票 |
| 导出 | Markdown / WeasyPrint / python-docx | 方案导出 |
| 认证 | **JWT** + bcrypt | 用户鉴权 |

### 1.3 七层架构

```text
客户端
  │ HTTP + SSE
  ▼
┌─ API 层 (FastAPI) ──────────── app/api/
│   路由注册、异常处理、依赖注入
└──────────┬────────────────────
           ▼
┌─ 编排层 (LangGraph) ───────── app/orchestrator/
│   五阶段 StateGraph、条件路由、重试循环
└──────────┬────────────────────
           ▼
┌─ Agent 层 ─────────────────── app/agents/
│   13 个专职 Agent，各自负责旅行规划的一个子领域
└──────────┬────────────────────
           ▼
┌─ 服务能力层 ───────────────── app/services/
│   LLM / RAG / 地图 / 天气 / 第三方
└──────────┬────────────────────
           ▼
┌─ 数据层 ───────────────────── app/db/
│   PostgreSQL + ChromaDB + Redis
└───────────────────────────────
```

依赖方向严格单向：`API → 编排 → Agent → 服务 → 数据`，禁止反向依赖。

---

## 2. 请求全流程：从 HTTP 到 SSE 响应

以一个典型请求为例——用户在聊天框输入"从武汉出发去北京玩3天，预算5000"：

```
Step 1: POST /api/v1/chat/sessions/{id}/messages
         ↓
Step 2: chat.py → send_message()
         保存用户消息到 DB（幂等去重）
         加载历史消息（最近 50 条）
         ↓
Step 3: _agent_sse_events() → _run_pipeline_events()
         创建 DeepSeekLLM 实例
         创建 UserInteractionAgent
         ↓
Step 4: UserInteractionAgent.stream_response()
         阶段1: 对话提取
          - LLM 分析完整对话历史
          - 提取结构化参数（origin/destination/days/budget/preferences）
          - 缺失字段逐项追问
          - 全部收集后展示确认卡片
          - 用户回复"确认" → ready=true, confirmed=true
         ↓
Step 5: orchestrator/pipeline.py → run_pipeline()
         构建 PlannerState（18 个字段）
         传入 LangGraph compiled graph
         ↓
Step 6: LangGraph 按图执行:
         parallel_planning → decision_r1 → detail_enrich
         → decision_r2 → plan_traffic → budget
         ↓
Step 7: BudgetAgent 输出 final_plan
         预算超标 → route_after_budget() → "retry"
         → adjust → parallel_planning（最多重试 2 次）
         预算 OK → "done" → END
         ↓
Step 8: 持久化结果到 conversation_plan_runs 表
         ↓
Step 9: SSE 流式返回给客户端
         event: step_start → progress(15%) → progress(30%) → ...
         → progress(100%) → event: done (含完整 summary)
```

**关键文件涉及**：
- `app/api/v1/chat.py` — SSE 流入口
- `app/agents/user_interaction_agent.py` — 意图识别 + 参数提取
- `app/orchestrator/pipeline.py` — 管线入口
- `app/orchestrator/graph.py` — LangGraph 图定义
- `app/orchestrator/nodes.py` — 8 个图节点

---

## 3. 入口与配置层

### 3.1 `main.py` — 项目启动入口

```python
# main.py (22 行)
def main():
    uvicorn.run(
        "app.api.router:app",   # ← FastAPI 应用实例
        host=settings.HOST,      # 0.0.0.0
        port=settings.PORT,      # 8000
        reload=settings.DEBUG,   # 开发模式热重载
        log_level=settings.LOG_LEVEL.lower(),
    )
```

**讲解要点**：极简入口，所有配置从 `Settings` 读取，符合十二要素 App 原则。

### 3.2 `app/config.py` — 全局配置

```python
class Settings(BaseSettings):      # pydantic-settings，自动读取 .env
    # 应用基础
    APP_NAME: str = "AI Travel Planner"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # JWT
    JWT_SECRET: str
    JWT_ACCESS_EXPIRE: int = 7200    # 2 小时
    JWT_REFRESH_EXPIRE: int = 604800 # 7 天

    # 数据库
    DATABASE_URL: str
    REDIS_URL: str

    # LLM（主模型 DeepSeek + 2 个备选）
    DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
    DOUBAO_API_KEY    / DOUBAO_BASE_URL    / DOUBAO_MODEL
    QWEN_API_KEY      / QWEN_BASE_URL

    # 地图 & 天气
    AMAP_API_KEY
    MEITUAN_TOKEN

    # RAG
    EMBEDDING_MODEL_ID = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024
    RAG_TOP_K = 40          # Chroma 召回数
    RAG_FINAL_K = 25        # Reranker 后保留数
    RERANKER_ENABLED = True

    class Config:
        env_file = ".env"   # 自动加载环境变量
```

**讲解要点**：
- `pydantic-settings` 自动从 `.env` 读取，类型安全
- 三种 LLM 共存，DeepSeek 为主
- RAG 参数可调（TOP_K / FINAL_K）
- `@field_validator("DEBUG")` 兼容 `"debug"/"dev"/"release"` 等字符串写法

---

## 4. API 层 — 路由与依赖注入

### 4.1 `app/api/router.py` — FastAPI 应用工厂

```python
# 核心结构 (76 行)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    meituan.sync_config_from_env()   # 启动时同步美团 CLI 配置
    yield

app = FastAPI(
    title=settings.APP_NAME,
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境关闭 Swagger
    lifespan=lifespan,
)

# 注册 8 个路由模块，统一前缀 /api/v1
app.include_router(chat_router,       prefix="/api/v1")
app.include_router(plan_router,       prefix="/api/v1")
app.include_router(trip_router,       prefix="/api/v1")
app.include_router(travelogue_router, prefix="/api/v1")
app.include_router(user_router,       prefix="/api/v1")
app.include_router(auth_router,       prefix="/api/v1")
app.include_router(data_router,       prefix="/api/v1")
app.include_router(ops_router,        prefix="/api/v1")

# 3 个全局异常处理器
@app.exception_handler(AppException)         # 业务异常 → 统一错误响应
@app.exception_handler(RequestValidationError) # Pydantic 校验失败 → 10001
@app.exception_handler(StarletteHTTPException)  # 404 等 HTTP 错误
```

**讲解要点**：
- `lifespan` 异步上下文管理器处理启动/关闭逻辑
- 生产环境关闭 `/docs` 避免暴露接口
- 所有路由统一 `/api/v1` 前缀，版本化 API
- 统一异常处理，对外不暴露堆栈信息

### 4.2 `app/exceptions.py` — 异常体系

```python
class AppException(Exception):       # 基类: code + http_status
class NotFoundException(AppException):     # 404, code=10003
class UnauthorizedException(AppException): # 401, code=20001
class BadRequestException(AppException):   # 400, code=10001
class LLMServiceException(AppException):   # 502, code=60003
class ExternalServiceException(AppException): # 502, code=60001
```

**讲解要点**：分层错误码——1xxxx 参数 / 2xxxx 认证 / 4xxxx 业务 / 5xxxx 服务端 / 6xxxx 外部服务。

### 4.3 `app/dependencies.py` — 依赖注入

```python
# 数据库会话（每次请求一个事务）
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()    # 成功自动提交
        except Exception:
            await session.rollback()  # 失败自动回滚
            raise

# 用户鉴权（JWT 优先 → 匿名会话兜底）
async def get_current_user(authorization, x_session_id, db):
    if x_session_id and not authorization:
        # 匿名用户: anon:md5(session_id)[:31]
        user_id = f"anon:{hashlib.md5(x_session_id.encode()).hexdigest()[:31]}"
        return {"user_id": user_id, "anonymous": True}
    # JWT 解析
    payload = decode_access_token(token)
    return {"user_id": payload["sub"], "anonymous": False}

# 服务层工厂函数（注入 Repository）
async def get_plan_service(db) -> TravelPlanService:
    return TravelPlanService(PlanRepository(db), UserRepository(db))

async def get_trip_service(db) -> TripService:
    return TripService(TripRepository(db), CheckinRepository(db), ...)
```

**讲解要点**：
- `get_db` 利用 `async with` + `try/except` 实现自动事务管理
- 匿名用户设计：客户端无需注册即可使用，数据通过 `X-Session-Id` 隔离
- 服务层通过 FastAPI `Depends()` 注入，声明式依赖管理

### 4.4 `app/api/v1/chat.py` — 核心聊天接口

这是整个系统最关键的 API 文件（343 行），包含：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/chat/sessions` | POST | 创建会话 |
| `/chat/sessions` | GET | 会话列表（分页） |
| `/chat/sessions/{id}` | DELETE | 删除会话 |
| `/chat/sessions/{id}` | PATCH | 更新标题/置顶 |
| **`/chat/sessions/{id}/messages`** | **POST** | **发送消息 → SSE 流（核心）** |
| `/chat/sessions/{id}/messages` | GET | 消息历史（支持页码/游标双模式） |
| `/chat/sessions/{id}/stream` | GET | SSE 重连恢复 |
| `/chat/sessions/{id}/plans` | GET | 会话内方案版本列表 |

**核心函数 `send_message()` 的执行流程**：

```python
@router.post("/sessions/{session_id}/messages")
async def send_message(session_id, request, current_user, service):
    # 1. 保存用户消息（幂等：相同 client_message_id 返回 idempotent_replay）
    _, created = await service.record_message(...)
    if not created:
        return sse_response(replay_events())  # 幂等重放

    # 2. 加载历史（最近 50 条）
    history = await _load_history(service, user_id, session_id)

    # 3. 返回 SSE 流
    return sse_response(_agent_sse_events(session_id, request.content, ...))
```

**`sse_response()` 函数**（64 行）：
- 使用 `asyncio.Queue` 作为生产者-消费者桥梁
- 15 秒 keepalive 心跳防止代理断开
- `_format_sse_frame()` 生成标准 SSE 格式：`id: evt_N\nevent: xxx\ndata: {...}\n\n`

---

## 5. 编排层 — LangGraph 五阶段管线

### 5.1 整体流程

```text
parallel_planning         ← AttractionAgent + FoodAgent + HotelAgent 并行
       │
       ▼
decision_r1               ← DecisionAgent.run_round1: 定稿景点(≤4/天)+餐厅
       │
       ▼
detail_enrich             ← DetailAgent: 美团/高德深度补充 Top 景点详情
       │
       ▼
decision_r2               ← DecisionAgent.run_round2: 按通勤评分选最优酒店
       │
       ▼
plan_traffic              ← TrafficAgent: 城际交通 + 每日路径规划
       │
       ▼
budget                    ← BudgetAgent: 预算核算 + 超支检测
       │
       ├── done → END
       └── retry → adjust → parallel_planning (降低酒店/餐饮预算后重跑)
```

### 5.2 `app/orchestrator/state.py` — 共享状态

```python
class PlannerState(TypedDict, total=False):
    # 用户输入
    user_id: str
    destination: str          # 目的地
    origin: str               # 出发地
    days: int                 # 天数
    total_budget: float       # 总预算
    reserve_budget: float     # 预留应急金
    planning_budget: float    # 规划预算 = total - reserve
    budget_no_limit: bool     # 预算不限
    preferences: list[str]    # 偏好标签
    cuisine_preferences: list[str]
    pace: str                 # 节奏：紧凑/适中/轻松
    preferred_transport: str  # 偏好交通
    hotel_star: int           # 酒店星级
    hotel_budget: float       # 酒店每晚预算
    meal_budget: float        # 餐饮每餐预算
    travelers: int

    # Agent 产出
    daily_plan: list[dict]    # AttractionAgent + DecisionAgent 产出
    meal_plan: list[dict]     # FoodAgent 产出
    hotel_plan: dict          # HotelAgent 产出
    traffic: dict             # TrafficAgent 产出
    final_plan: dict          # BudgetAgent 最终产出

    # 循环控制
    retry_count: int          # 当前重试次数
    adjusted_params: dict     # 调整后的参数
    should_retry: bool        # 是否需要重试
```

**讲解要点**：`TypedDict` 定义图状态，LangGraph 自动在节点间传递和合并；`messages` 字段用 `add_messages` reducer 实现追加而非覆盖。

### 5.3 `app/orchestrator/graph.py` — 图定义

```python
def build_graph() -> StateGraph:
    w = StateGraph(PlannerState)

    # 8 个节点
    w.add_node("parallel_planning", node_parallel_planning)
    w.add_node("decision_r1",      node_decision_r1)
    w.add_node("detail_enrich",    node_detail_enrich)
    w.add_node("decision_r2",      node_decision_r2)
    w.add_node("plan_traffic",     node_traffic)
    w.add_node("budget",           node_budget)
    w.add_node("adjust",           node_adjust_params)

    w.set_entry_point("parallel_planning")

    # 直线边
    w.add_edge("parallel_planning", "decision_r1")
    w.add_edge("decision_r1",      "detail_enrich")
    w.add_edge("detail_enrich",    "decision_r2")
    w.add_edge("decision_r2",      "plan_traffic")
    w.add_edge("plan_traffic",     "budget")

    # 条件边：budget → END 或 adjust → parallel_planning（循环）
    w.add_conditional_edges("budget", route_after_budget, {
        "done": END,
        "retry": "adjust",
    })
    w.add_edge("adjust", "parallel_planning")

    return w.compile()
```

**讲解要点**：
- 直线边（`add_edge`）表示确定性的下一步
- 条件边（`add_conditional_edges`）根据 `route_after_budget()` 返回值路由
- 循环边 `adjust → parallel_planning` 形成超预算重试闭合环路
- 最大重试次数由 BudgetAgent 内部控制（默认 2 次）

### 5.4 `app/orchestrator/nodes.py` — 8 个节点实现

**`node_parallel_planning`**（最关键的并行节点）：
```python
async def node_parallel_planning(state) -> dict:
    # 三个 Agent 并行执行
    attr_t = AttractionAgent(llm).run({...})
    food_t = FoodAgent(llm).run({...})
    hotel_t = HotelAgent(llm).run({...})
    attr, food, hotel = await asyncio.gather(attr_t, food_t, hotel_t)
    # 合并结果 → 去重
    return {"daily_plan": deduped, "meal_plan": ..., "hotel_plan": ...}
```

**`node_budget`**（预算核算节点）：
- 汇总景点门票、餐饮、酒店、交通四项花费
- 传入 BudgetAgent 进行核算
- 标注无数据类目（`spent=0, budget>0 → status="no_data"`）
- 发回 `should_retry` 信号

**`node_adjust_params`**（参数调整节点）：
- 接收 `adjusted_params`（降低后的酒店/餐饮预算）
- 写入 state 供下一轮 parallel_planning 使用
- 硬地板保护：`hotel_budget ≥ 200`、`meal_budget ≥ 50`

**`route_after_budget`**（条件路由）：
```python
def route_after_budget(state) -> str:
    return "retry" if state.get("should_retry") else "done"
```

### 5.5 `app/orchestrator/pipeline.py` — SSE 管线入口

```python
async def run_pipeline(params: dict) -> AsyncIterator[tuple[str, dict]]:
    # 1. 未确认 → 返回 waiting_confirmation
    if not params.get("confirmed"):
        yield ("done", {"status": "waiting_confirmation"})
        return

    # 2. 构建初始状态 (18 个字段)
    initial: PlannerState = {...}

    # 3. LangGraph 流式执行
    async for update in planner_graph.astream(initial, stream_mode="updates"):
        for node_name, node_update in update.items():
            final_state.update(node_update)
            # 每个节点完成 → 推 SSE progress 事件
            yield ("progress", {"step": stage, "percent": 15→30→45→...→100})

    # 4. 完成 → 推 final_plan
    yield ("done", {"summary": final_state["final_plan"]})
```

**讲解要点**：
- `astream(stream_mode="updates")` 是 LangGraph 的流式 API，每个节点完成时 yield
- `stage_progress` 字典将节点名映射到进度百分比，给前端进度条
- 异常捕获 → `("error", ...)` SSE 事件

---

## 6. Agent 层 — 智能体体系

### 6.1 架构总览

```
                    BaseAgent (ABC)
                   /    |    |     \
          UserInteraction  |  Traffic  Budget  ...
          /        \
  AttractionAgent  FoodAgent  HotelAgent  DecisionAgent  DetailAgent
```

**13 个 Agent**：

| Agent | 职责 | 编排方式 |
|-------|------|---------|
| **UserInteractionAgent** | 意图识别 + 参数提取 + 确认 | 独立（pipeline 前） |
| **AttractionAgent** | RAG 搜索景点 → LLM 日计划 | LangGraph parallel |
| **FoodAgent** | RAG 搜索餐厅 → LLM 三餐安排 | LangGraph parallel |
| **HotelAgent** | 美团 CLI → Chroma → 高德三级降级 | LangGraph parallel |
| **DecisionAgent** | R1 定稿景点+餐厅 / R2 通勤评分选酒店 | LangGraph 节点 |
| **DetailAgent** | 美团/高德补充 Top 景点详情 | LangGraph 节点 |
| **TrafficAgent** | 城际交通 + 每日路径规划 | LangGraph 节点 |
| **BudgetAgent** | 预算核算 + 动态分配 + 超支检测 | LangGraph 节点 |
| **AdjustAgent** | 天气/时间/预算触发调整 | LangGraph 节点 |
| **WeatherAgent** | 目的地天气查询 | 预留（未挂入主编排） |
| **RouteOptimizerAgent** | 路径优化 | 预留 |
| **SouvenirAgent** | 纪念品推荐 | 预留 |
| **TripAgent** | 行程执行（签到/进度/提醒） | 独立调用 |
| **TravelogueAgent** | AI 游记生成 + 照片标注 + 社交素材 | 独立调用 |

### 6.2 `app/agents/base.py` — Agent 基类

这是最值得逐行讲解的文件之一（192 行），定义了所有 Agent 的公共行为：

```python
class BaseAgent(ABC):
    name: str = "base"
    description: str = "Base agent"

    def __init__(self, llm: BaseLLM):
        self.llm = llm           # LLM 实例
        self.tools: list[dict] = []  # Function Calling 工具定义
        self._context: dict = {}     # 上下文数据
```

**核心方法**：

1. **`register_tools_from_registry(names)`** — 从全局工具注册表按名称注册工具
2. **`execute_tools(messages, temperature, max_turns=3)`** — Function Calling 循环：
   ```
   LLM 决策 → 工具调用 → 结果回传 → LLM 再决策 → ...（最多 3 轮）
   ```
3. **`call_llm(messages, temperature, max_retries=3)`** — LLM 调用 + 指数退避重试
4. **`validate_output(data, SchemaClass)`** — Pydantic 校验 + 字段缺失自动补默认值
5. **`get_system_prompt()`** — 从 PromptManager 获取 Agent 专属系统提示词

**讲解要点**：
- `execute_tools` 工具调用循环的设计——先让 LLM 决定调用哪些工具，再执行并将结果回传
- 指数退避重试：1.5^attempt 秒
- `validate_output` 的容错策略：校验失败不抛异常，而是尽力合并默认值

### 6.3 `app/agents/user_interaction_agent.py` — 用户交互 Agent

最复杂的 Agent（1114 行），负责理解用户意图和收集规划参数。

**核心流程**：
```python
async def run(input_data):
    1. _prepare_history()         # 拼接对话历史
    2. _analyze()                 # LLM 分析：mode + extracted 参数
    3. _build_result()            # 根据状态返回不同响应
       ├── daily_chat → 闲聊回复
       ├── collecting (missing) → 追问缺失字段
       ├── awaiting_confirmation → 展示确认卡片
       └── confirmed → ready=true, 触发 pipeline
```

**状态机**：
```
daily_chat ←→ collecting ←→ awaiting_confirmation → confirmed → pipeline
    ↑_______________↓
```

**关键设计**：
- **确认标记**：`CONFIRMATION_MARKER = "确认后我再开始生成完整方案，可以吗？"`
- **确认检测**：`_is_confirmed()` 检查上一轮 assistant 是否包含确认标记 + 当前用户是否正面回复
- **修正检测**：`_looks_like_revision()` — 用户说"确认，但是预算改成8000" → 不视为确认
- **新规划识别**：`_current_turn_intent()` — 正则匹配"重新规划""生成方案"等
- **字段继承**：`_apply_inherited_fields()` — "其他不变，换成上海" → 继承上次配置
- **预算拆分**：支持"总预算5000，留1000应急" → reserve_budget=1000, planning_budget=4000

### 6.4 `app/agents/attraction_agent.py` — 景点规划 Agent

RAG 驱动的景点规划（200 行）。

**三级数据获取策略**：
```
Chroma RAG (BGE-M3 语义搜索)
  → 候选 < 3 个？
    → 高德 POI 实时搜索 (poi_live.py)
      → 仍不足？使用已有候选（即使很少）
```

**LLM 规划 prompt 设计**：
- 显式列出所有候选景点（含坐标、评分、价格）
- 要求只能从候选列表中选择，禁止编造
- 景点名必须原样复制，保留 POI 坐标

**去重机制**：`node_parallel_planning` 中的 `_dedupe_daily_plan()` 函数——"故宫博物院(含珍宝馆)" 和 "故宫博物院" 识别为同一景点。

### 6.5 `app/agents/decision_agent.py` — 两轮决策 Agent

**确定性算法，不走 LLM**（83 行）。

| 轮次 | 输入 | 输出 | 逻辑 |
|------|------|------|------|
| R1 | daily_plan + meal_plan | 定稿版 (≤4 景点/天) | 按候选顺序取前 4，超过则标记 auto_trimmed |
| R2 | hotel_plan + daily_plan | 选中最优酒店 | `TrafficAgent.evaluate_hotels()` 计算通勤评分，选最高分 |

**R2 酒店选择的核心**：不是简单的排序，而是**模拟真实用户通勤体验**——对每个候选酒店，计算从酒店出发到每天第一个景点的交通时间和距离，生成 `commute_score`。

### 6.6 其他重要 Agent 简介

**HotelAgent** — 三级数据源降级：
```
美团 CLI (mttravel, 60s 超时, 真实价格+图片)
  → 失败/无结果 → Chroma RAG (向量语义搜索)
    → 候选 < 3 → 高德 POI 实时搜索
```

**BudgetAgent** — 动态预算分配：
- 按城市等级（一线/新一线/二线/三线）分配住宿权重
- 按偏好调整景点/餐饮分配比例
- 超支检测：`spent > total_budget`
- 重试信号生成：降低 hotel_budget / meal_budget 参数发回 adjust 节点

**TrafficAgent** — 交通规划：
- 大交通：12306 爬虫获取高铁/动车票价
- 市内交通：高德 direction API 计算每日路径
- 时间约束：景点游览时长 + 用餐时长 + 交通时间 ≤ 每日可用时间

---

## 7. 工具系统 — Function Calling

### 7.1 `app/agents/tools/tool_registry.py` — 全局工具注册表

```python
# 注册工具
register("tool_name", "description", {parameters_schema}, handler_function)

# 获取工具
get_tool_defs()           # → 所有工具定义列表（OpenAI Function Calling 格式）
get_handler("tool_name")  # → 工具执行函数
```

### 7.2 已注册工具一览

| 工具名 | 数据来源 | 用途 |
|--------|---------|------|
| `search_attractions` | Chroma RAG | 景点语义搜索 |
| `search_restaurants` | Chroma RAG | 餐厅语义搜索 |
| `search_hotels` | Chroma RAG | 酒店语义搜索 |
| `get_weather` | 高德天气 API | 天气查询 |
| `get_route` | 高德 direction API | 路径规划 |
| `meituan_travel` | mttravel CLI | 酒店/景点/行程（真实价格） |
| `railway_search_*` | 12306 爬虫 | 火车票余票/票价 |

---

## 8. 服务层 — LLM / RAG / 地图 / 第三方

### 8.1 LLM 服务

**`app/services/llm/base.py`** — 抽象基类：
```python
class BaseLLM(ABC):
    api_key / base_url / model
    async chat(messages, temperature) → str
    async chat_stream(messages, temperature) → AsyncIterator[str]
    async chat_with_tools(messages, tools, temperature) → dict
```

**`app/services/llm/deepseek.py`** — DeepSeek 实现（79 行）：
- 基于 OpenAI 兼容接口，使用 `AsyncOpenAI` 客户端
- `chat_with_tools` 返回 `message.model_dump()`，兼容 Function Calling

**`app/services/llm/prompt_manager.py`** — 系统提示词管理：
- 每个 Agent 名称 → 对应的 system prompt
- 集中管理，便于调优和 A/B 测试

### 8.2 RAG 系统

**检索全流程**：
```
用户查询 "北京历史人文景点适合亲子"
  → EmbeddingService.embed_query() → 1024 维向量
    → ChromaDB.search(collection="attractions", top_k=40)
      → RerankerService.rerank() → BGE-reranker-base 重排 → 取前 25
        → composite_score() 综合评分
          语义相关度(50%) + 评分(25%) + 标签匹配(15%) + 价格(10%)
```

**关键参数**（`config.py`）：
- `EMBEDDING_MODEL_ID = "BAAI/bge-m3"` — 1024 维中文优化
- `RAG_TOP_K = 40` — Chroma 召回数量
- `RAG_FINAL_K = 25` — Reranker 后保留数量
- `RERANKER_ENABLED = True` — 是否启用重排

**`app/services/vector/rag.py`** — RAG 检索入口（108 行）：
```python
async def rag_search(collection_name, query, where, top_k, final_k, ...):
    query_embedding = await embedding_service.embed_query(query)
    result = vector_store.search(collection_name, query_embedding, ...)
    candidates = _build_candidates(result)
    if reranker_enabled:
        candidates = await reranker_service.rerank(query, candidates)  # BGE reranker
    return composite_score(candidates, preferences, max_price, min_rating)
```

### 8.3 地图服务 (`app/services/map/amap.py`)

高德 Web API 封装：
- POI 搜索（景点/餐厅/酒店）
- 正/逆地理编码
- 驾车/步行/公交路径规划（direction API）
- 天气查询（通过高德天气接口）

### 8.4 第三方服务 (`app/services/third_party/`)

- **`meituan.py`** — 美团酒旅 CLI 封装（subprocess 调用 `mttravel`）
- **`poi_live.py`** — 高德 POI 实时搜索兜底
- **`railway12306.py`** — 12306 火车票爬虫

---

## 9. 数据层 — ORM / Repository / 迁移

### 9.1 数据库模型 (`app/db/models/`)

**3 个基础 Mixin**（`base.py`）：

```python
class UUIDMixin:       # id = Column(String(36), PK, default=uuid4)
class TimestampMixin:  # created_at, updated_at
class SoftDeleteMixin: # deleted_at, is_deleted, soft_delete()
```

**13 张业务表**：

| 表 | 模型 | 核心用途 |
|----|------|---------|
| `users` | User | 用户账号 + 偏好 |
| `conversations` | Conversation | 对话会话 |
| `messages` | Message | 聊天消息（含 client_message_id 幂等） |
| `conversation_plan_runs` | ConversationPlanRun | 会话内方案版本 |
| `plans` | Plan | 旅行方案（含完整 itinerary JSON） |
| `trip_states` | TripState | 行程执行状态 |
| `checkins` | Checkin | POI 签到 |
| `expense_records` | ExpenseRecord | 消费记录 |
| `adjustments` | Adjustment | 行程调整记录 |
| `attractions` | Attraction | 景点 POI 数据 |
| `hotels` | Hotel | 酒店 POI 数据 |
| `restaurants` | Restaurant | 餐厅 POI 数据 |
| `travelogues` | Travelogue | AI 游记 |
| `social_materials` | SocialMaterial | 社交素材（九宫格等） |
| `shares` | Share | 分享链接 |

**POI 表特殊设计**：
- `source` + `source_poi_id` 联合唯一约束 — 同一外部 POI 不会重复入库
- 所有 POI 表都有 `latitude/longitude`、`rating`、`tags(JSON)`

### 9.2 Repository 模式 (`app/db/repositories/`)

```python
class BaseRepository(Generic[T]):
    async get_by_id(id) → T | None
    async get_all(filters) → list[T]
    async count(filters) → int
    async create(data) → T
    async update(id, data) → T
    async delete(id) → None
```

每个业务实体有独立 Repository 子类，封装特定查询逻辑：
- `UserRepository.find_by_phone()`
- `PlanRepository.list_by_user()` / `count_by_user()`
- `ConversationRepository.add_message()` / `list_plan_runs()`

**设计原则**：API 层和 Agent 层绝不直接操作 ORM Session，全部通过 Repository。

### 9.3 数据库会话 (`app/db/session.py`)

```python
engine = create_async_engine(DATABASE_URL, echo=DEBUG, pool_size=20)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

### 9.4 迁移管理 (`app/db/migrations/`)

使用 Alembic 异步迁移：
```bash
alembic revision --autogenerate -m "描述"  # 生成迁移
alembic upgrade head                        # 执行迁移
```

---

## 10. Schema 层 — Pydantic 校验体系

### 10.1 统一响应格式 (`app/schemas/common.py`)

```json
// 成功
{"code": 0, "message": "ok", "data": {...}, "request_id": "req_abc123"}

// 失败
{"code": 10001, "message": "Bad request", "data": null, "request_id": "req_abc123"}
```

**核心类型**：
- `BaseResponse[T]` — 泛型成功响应包装
- `PaginatedData[T]` — 页码分页（list/total/page/page_size/total_pages）
- `CursorPaginatedData[T]` — 游标分页（list/has_more/next_before_id/next_after_id）
- `ErrorResponse` — 错误响应（不暴露堆栈/SQL/密钥）
- `TaskStatus` — 异步导出任务状态

### 10.2 Agent 输出 Schema (`app/schemas/agent_outputs.py`)

每个 Agent 输出都经过 Pydantic 校验，字段缺失自动补默认值。关键 Schema：

- `AttractionItem` — 景点（name, reason, duration_hours, price, lat/lng, ...）
- `DayPlan` — 每日景点列表
- `HotelRec` — 酒店推荐（含 commute_score 通勤评分）
- `BudgetDetail` — 预算明细（category, budget, spent, remaining, status）
- `TrafficSegment` — 交通段（from/to, distance_km, time_min, cost, mode）

---

## 11. SSE 流式架构

### 11.1 为什么用 SSE

- 单向服务器推送（不需要 WebSocket 的双向）
- 原生 `text/event-stream` 协议，浏览器 `EventSource` 直接支持
- Nginx 兼容性好（需关闭 buffering）

### 11.2 实现细节

**`_format_sse_frame()`**：
```python
def _format_sse_frame(event_id, event, data):
    return f"id: evt_{event_id}\nevent: {event}\ndata: {json.dumps(data)}\n\n"
```

**生产者-消费者模式**：
```python
# 生产者 (async task)
async def _enqueue_sse_events(events, queue):
    async for item in events:
        await queue.put(item)
    await queue.put(_SSE_DONE)  # 终止信号

# 消费者 (async generator)
async def stream():
    while True:
        item = await asyncio.wait_for(queue.get(), timeout=15.0)  # 15s keepalive
        if item is _SSE_DONE: break
        yield _format_sse_frame(...)
```

**SSE 事件类型**：
| event | 含义 | data 内容 |
|-------|------|-----------|
| `step_start` | 阶段开始 | `{step, label}` |
| `progress` | 阶段完成 | `{step, percent, message}` |
| `message_delta` | 流式文本 | `{role, content_delta}` |
| `message` | 完整消息 | `{role, content}` |
| `step_end` | 阶段结束 | `{step}` |
| `done` | 完成 | `{status, summary/plan_id/...}` |
| `error` | 错误 | `{message}` |

### 11.3 幂等重放

消息表中 `client_message_id` 有唯一约束。重复发送返回：
```json
{"event": "done", "data": {"status": "idempotent_replay", "client_message_id": "xxx"}}
```

---

## 12. 异常与错误处理

### 12.1 异常层级

```
AppException (基类)
├── NotFoundException       (404, code=10003)
├── UnauthorizedException   (401, code=20001)
├── BadRequestException     (400, code=10001)
├── PlanExportFormatException (400, code=40006)
├── LLMServiceException     (502, code=60003)
├── ExternalServiceException (502, code=60001)
└── NotImplementedAppException (202, code=70002)
```

### 12.2 错误码规范

| 范围 | 含义 |
|------|------|
| `0` | 成功 |
| `1xxxx` | 参数/校验错误 |
| `2xxxx` | 认证/授权 |
| `3xxxx` | 业务规则限制 |
| `4xxxx` | 业务资源（导出/分享等） |
| `5xxxx` | 服务端内部错误 |
| `6xxxx` | 外部服务调用失败 |
| `7xxxx` | 预留但未实现的能力 |

### 12.3 全局异常处理器

```python
@app.exception_handler(AppException)         # 所有业务异常统一包装
@app.exception_handler(RequestValidationError) # Pydantic 校验 → 10001 + "Bad request"
@app.exception_handler(StarletteHTTPException)  # 404 → 10003 + "Resource not found"
```

**安全设计**：异常响应只返回 `code` + `message`，不暴露堆栈、SQL、文件路径等内部信息。

---

## 13. 讲解建议 — 推荐逐行讲解的文件

### 13.1 按讲解深度推荐

**第一层：架构概览（必讲）**
| 文件 | 行数 | 讲解要点 |
|------|------|---------|
| `main.py` | 22 | 极简入口 |
| `app/config.py` | 88 | pydantic-settings + .env + LLM/RAG 参数 |
| `app/api/router.py` | 76 | FastAPI 工厂 + 8 路由注册 + 异常处理 |
| `app/dependencies.py` | 121 | DI 注入 + JWT 鉴权 + 匿名用户 |
| `app/exceptions.py` | 68 | 分层错误码体系 |

**第二层：核心编排（重点讲）**
| 文件 | 行数 | 讲解要点 |
|------|------|---------|
| `app/orchestrator/state.py` | 44 | PlannerState TypedDict 设计 |
| `app/orchestrator/graph.py` | 68 | LangGraph 图构建 + 条件边 |
| `app/orchestrator/nodes.py` | 240 | 8 个节点实现 + asyncio.gather 并行 |
| `app/orchestrator/pipeline.py` | 103 | SSE 流式管线入口 |

**第三层：Agent 体系（核心亮点）**
| 文件 | 行数 | 讲解要点 |
|------|------|---------|
| `app/agents/base.py` | 192 | BaseAgent 基类 + 工具调用循环 + 重试 |
| `app/agents/user_interaction_agent.py` | 1114 | 意图识别 + 状态机 + 确认流程 |
| `app/agents/attraction_agent.py` | 200 | RAG → LLM 规划 + 三级数据源降级 |
| `app/agents/decision_agent.py` | 83 | 确定性两轮决策（不走 LLM） |

**第四层：SSE 流式（展示用）**
| 文件 | 行数 | 讲解要点 |
|------|------|---------|
| `app/api/v1/chat.py` | 343 | SSE 生产者-消费者 + _run_pipeline_events |
| `app/schemas/common.py` | 104 | BaseResponse / 分页 / 错误响应 |

### 13.2 按讲解时长推荐

**15 分钟速览**：`main.py` → `config.py` → `router.py` → `graph.py` → `nodes.py` → `chat.py` (send_message 部分)

**30 分钟精讲**：上 + `dependencies.py` → `base.py` → `user_interaction_agent.py`（核心方法）→ `attraction_agent.py` → `pipeline.py`

**60 分钟完整**：全部核心文件 + `decision_agent.py` → `state.py` → `rag.py` → `agent_outputs.py`

### 13.3 讲解主线建议

以**一个真实请求的完整生命周期**为主线：

```
main.py 启动
  → config.py 加载配置
    → router.py 注册路由
      → chat.py send_message() 接收请求
        → dependencies.py 鉴权 + 注入 DB
          → user_interaction_agent.py 解析意图
            → pipeline.py 启动管线
              → graph.py 执行 LangGraph
                → nodes.py 并行规划 + 两轮决策 + 预算
                  → base.py 工具调用 + 重试
                    → attraction_agent.py RAG 搜索 + LLM 规划
                      → chat.py sse_response 流式返回
```

---

## 附录：完整文件索引

```
main.py                              # 入口
app/
├── config.py                        # 全局配置
├── dependencies.py                  # 依赖注入
├── exceptions.py                    # 异常体系
├── api/
│   ├── router.py                    # FastAPI 工厂
│   └── v1/
│       ├── auth.py                  # 注册/登录/Token
│       ├── chat.py                  # ★ 核心：SSE 聊天
│       ├── data.py                  # POI 数据查询
│       ├── ops.py                   # 健康检查/导出任务
│       ├── plan.py                  # 方案 CRUD/导出/分享
│       ├── travelogue.py            # 游记/社交素材
│       ├── trip.py                  # 行程执行
│       └── user.py                  # 用户资料
├── orchestrator/
│   ├── state.py                     # PlannerState
│   ├── graph.py                     # ★ LangGraph 图
│   ├── nodes.py                     # ★ 8 个图节点
│   ├── pipeline.py                  # ★ SSE 管线
│   ├── planner.py                   # 规划辅助
│   └── conflict_detection.py        # 冲突检测
├── agents/
│   ├── base.py                      # ★ Agent 基类
│   ├── context.py                   # PlanContext
│   ├── user_interaction_agent.py    # ★ 意图识别
│   ├── attraction_agent.py          # ★ 景点规划
│   ├── food_agent.py                # 美食推荐
│   ├── hotel_agent.py               # 酒店推荐
│   ├── traffic_agent.py             # 交通规划
│   ├── budget_agent.py              # 预算核算
│   ├── decision_agent.py            # ★ 两轮决策
│   ├── detail_agent.py              # 详情补全
│   ├── weather_agent.py             # 天气查询
│   ├── adjust_agent.py              # 动态调整
│   ├── route_optimizer_agent.py     # 路径优化
│   ├── souvenir_agent.py            # 纪念品
│   ├── travelogue_agent.py          # 游记
│   ├── trip_agent.py                # 行程执行
│   └── tools/
│       ├── tool_registry.py         # 工具注册表
│       ├── attraction_tools.py      # 景点工具
│       ├── budget_tools.py          # 预算工具
│       ├── map_tools.py             # 地图工具
│       └── weather_tools.py         # 天气工具
├── schemas/
│   ├── common.py                    # 统一响应/分页
│   ├── agent_outputs.py             # ★ Agent 输出 Schema
│   ├── chat.py / plan.py / ...      # 各领域 Schema
├── services/
│   ├── llm/
│   │   ├── base.py                  # LLM 抽象
│   │   ├── deepseek.py              # ★ DeepSeek 实现
│   │   ├── doubao.py / qwen.py      # 备选 LLM
│   │   └── prompt_manager.py        # 提示词管理
│   ├── vector/
│   │   ├── embedding.py             # BGE-M3 embedding
│   │   ├── vector_store.py          # ChromaDB 封装
│   │   ├── rag.py                   # ★ RAG 检索
│   │   ├── reranker.py              # BGE reranker
│   │   └── scorer.py                # 综合评分
│   ├── map/amap.py                  # 高德 API
│   ├── weather/qweather.py          # 天气适配
│   └── third_party/                 # 美团/12306
├── db/
│   ├── session.py                   # 异步引擎
│   ├── models/                      # 13 张表 ORM
│   ├── repositories/                # DAO 层
│   └── migrations/                  # Alembic
└── utils/
    ├── logger.py                    # Loguru 配置
    ├── cache.py                     # Redis 封装
    └── validator.py                 # 输入校验
```
