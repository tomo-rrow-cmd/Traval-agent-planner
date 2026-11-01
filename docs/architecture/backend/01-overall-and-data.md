# 整体架构与数据库

> 供团队协作参考，覆盖当前后端实现中的整体分层和数据库实现快照。正式协作边界以 `.agent/` 和 `docs/` 专题文档为准。

## 一、整体架构（七层）

```text
客户端 (Web/H5)
    │ HTTP + SSE
    ▼
┌─ 接入层 ──────────────────────────────────────────┐
│  Nginx / API Gateway / JWT 鉴权 / 限流 / 日志      │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ API 层 (FastAPI) ────────────────────────────────┐
│  app/api/router.py         总路由                  │
│  app/api/v1/chat.py        对话接口                │
│  app/api/v1/plan.py        方案接口                │
│  app/api/v1/user.py        用户接口                │
│  app/api/v1/auth.py        认证接口（契约 MVP）      │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 编排层 (LangGraph) ───────────────────────────────┐
│  app/orchestrator/planner.py  TravelPlanner       │
│  app/orchestrator/graph.py    LangGraph 工作流图   │
│  app/orchestrator/nodes.py    当前规划节点实现      │
│  app/orchestrator/state.py    PlannerState 状态    │
│  app/orchestrator/conflict_detection.py 冲突检测   │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 智能体层 ────────────────────────────────────────┐
│  app/agents/base.py           基类 (LLM/重试/工具) │
│  app/agents/user_interaction_agent.py  对话入口    │
│  app/agents/attraction_agent.py       景点规划     │
│  app/agents/food_agent.py             美食推荐     │
│  app/agents/hotel_agent.py            住宿推荐     │
│  app/agents/traffic_agent.py          交通规划     │
│  app/agents/budget_agent.py           预算管理     │
│  app/agents/decision_agent.py         两轮决策     │
│  app/agents/detail_agent.py           详情补全     │
│  weather/route_optimizer/souvenir     可复用模块   │
│  app/agents/tools/                   工具注册表    │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 服务能力层 ──────────────────────────────────────┐
│  app/services/llm/         LLM (DeepSeek/豆包/千问)│
│  app/services/map/         高德地图 (POI/路径)      │
│  app/services/weather/     高德天气适配             │
│  app/services/vector/      BGE embedding + Chroma   │
│  app/services/third_party/ 美团酒旅 CLI / 12306     │
└────────────────────────────────────────────────────┘
    │
    ▼
┌─ 数据存储层 ──────────────────────────────────────┐
│  PostgreSQL    业务数据 (8 张表)                   │
│  Chroma        向量库 (3 个 collection)            │
│  Redis         缓存/会话/锁 (预留)                 │
│  文件系统       Chroma 本地数据、导出文件等          │
└────────────────────────────────────────────────────┘
```

依赖方向：`API → 编排层 → 智能体层 → 服务能力层 → 数据存储层`，严禁反向依赖。

## 二、数据库设计

### 2.1 PostgreSQL — 8 张表

#### `users` — 用户表

```text
id (UUID PK)          username (UNIQUE)     email (UNIQUE)
phone (UNIQUE)         hashed_password        nickname
avatar                 preferences (JSON)     created_at / updated_at
```

#### `conversations` — 会话表

```text
id (UUID PK)          user_id                title
status                destination            days
plan_id               created_at             updated_at
```

- `status`: active / completed / archived

#### `messages` — 消息表

```text
id (UUID PK)          conversation_id (FK)   role (user/assistant/system)
content (TEXT)        sequence (INT)         created_at / updated_at
```

- 按 `sequence` 排序；当前读取接口默认最多加载 50 条，不会自动删除更早消息。

#### `conversation_plan_runs` — 会话方案版本表

```text
id (UUID PK)          conversation_id (FK)  sequence
destination          days                  summary (JSON)
created_at / updated_at
```

- 每次成功生成完整方案新增一行，不覆盖同会话旧版本。
- `summary` 保存 pipeline 最终结构化结果；`conversations.plan_id` 指向最新版本。
- 该表服务于聊天上下文和会话内历史版本，不替代长期方案表 `plans`。

#### `plans` — 旅行方案表

```text
id (UUID PK)          user_id (FK)           destination
start_date / end_date  budget                 travelers
preferences (JSON)     status                 itinerary (JSON)
total_cost             created_at / updated_at
```

#### `attractions` — 景点表

```text
id (UUID PK)          name                   city
category              latitude / longitude   address
rating                price                  opening_hours
recommended_duration  tags (JSON)            image_url
description           created_at / updated_at
```

- 数据来源：高德 POI 搜索 → `seed_poi.py`。
- 景点、餐厅、酒店都包含 `source`、`source_poi_id`，并以二者的联合唯一约束提供稳定外部身份。

#### `restaurants` — 餐厅表

```text
id (UUID PK)          name                   city
cuisine               latitude / longitude   address
rating                avg_price              opening_hours
tags (JSON)           image_url              description
created_at / updated_at
```

#### `hotels` — 酒店表

```text
id (UUID PK)          name                   city
star                  latitude / longitude   address
rating                price_per_night        amenities (JSON)
image_url             description            created_at / updated_at
```

### 2.2 迁移管理

```text
app/db/migrations/
├── env.py             # Alembic 环境配置
├── script.py.mako     # 迁移脚本模板
└── versions/          # 迁移历史文件
```

- 生成迁移：`alembic revision --autogenerate -m "描述"`
- 执行迁移：`alembic upgrade head`
- 当前迁移链包含 `conversation_plan_runs` 建表，以及 POI `source/source_poi_id` 稳定身份字段。
