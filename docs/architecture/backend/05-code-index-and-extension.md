# 关键文件索引与扩展指南

## 1. 关键文件索引

```text
项目根/
├── app/
│   ├── agents/             智能体层
│   │   ├── base.py             基类 (LLM / 重试 / 工具)
│   │   ├── tools/tool_registry.py  Function Calling 工具注册入口
│   │   ├── user_interaction_agent.py
│   │   ├── attraction_agent.py
│   │   ├── food_agent.py
│   │   ├── hotel_agent.py
│   │   ├── traffic_agent.py
│   │   ├── budget_agent.py
│   │   ├── weather_agent.py
│   │   ├── route_optimizer_agent.py
│   │   └── souvenir_agent.py
│   │
│   ├── api/                接口层
│   │   ├── router.py
│   │   └── v1/{auth,chat,data,ops,plan,user}.py
│   │
│   ├── orchestrator/       编排层
│   │   ├── planner.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   └── conflict_detection.py
│   │
│   ├── schemas/            数据模型
│   │   ├── common.py           统一响应
│   │   ├── agent_outputs.py    Agent 输出 Schema
│   │   ├── chat.py / data.py / plan.py / user.py
│   │
│   ├── services/           服务层
│   │   ├── llm/{base,deepseek,doubao,qwen,prompt_manager}.py
│   │   ├── map/{amap,geocode}.py
│   │   ├── weather/qweather.py
│   │   ├── vector/{embedding,rag,reranker,vector_store}.py
│   │   ├── third_party/{meituan,railway12306}.py
│   │   ├── data/{attraction_service,hotel_service,restaurant_service}.py
│   │   └── application/    业务服务层
│   │
│   ├── db/                 数据层
│   │   ├── session.py
│   │   ├── models/            ORM 模型
│   │   ├── repositories/     DAO 层
│   │   └── migrations/       Alembic
│   │
│   └── utils/              工具
│       ├── logger.py
│       ├── cache.py
│       └── validator.py
│
├── docs/
│   └── architecture/
│       ├── backend/        后端实现架构快照
│       ├── implementation/ 工程实现边界
│       └── snapshots/      代码结构快照
├── scripts/
│   ├── start_backend.sh    Linux/macOS 后端一键启动
│   ├── start_backend.ps1   Windows PowerShell 后端一键启动
│   ├── start_backend.cmd   Windows CMD 启动包装器
│   ├── init_db.py          数据库初始化
│   ├── rebuild_vectors.py  从 PostgreSQL 重建 Chroma 向量库
│   ├── seed_poi.py         POI 数据拉取
│   ├── test_agent.py       Agent 手动测试脚本
│   └── test_pipeline.py    端到端管线手动测试脚本
│
├── tests/
│   ├── test_api.py         API 契约测试
│   ├── test_agents.py      Agent 冒烟测试
│   └── test_llm.py         LLM Mock 测试
│
├── .env                    环境变量 (不提交 Git)
├── .env.example            环境变量示例
├── requirements.txt        Python 依赖
└── README.md               项目说明
```

完整仓库结构以 [当前代码结构快照](../snapshots/code-structure.md) 为准。

## 2. 扩展指南

### 新增 Agent

1. 继承 `BaseAgent`，实现 `run(input_data) -> dict`。
2. 在 `agent_outputs.py` 添加输出 Schema。
3. 在 `nodes.py` 添加编排节点。
4. 在 `graph.py` 注册节点和边。
5. 在 `chat.py` 的 `run_planning()` 调用。

### 新增工具

1. 在 `tool_registry.py` 写 handler 函数和 `register()`。
2. 在 Agent `__init__` 中 `register_tools_from_registry(["name"])`。

### 新增数据源

1. 在 `services/third_party/` 新建适配器。
2. 在 `tool_registry.py` 注册为工具。
3. Agent 调用新工具获取数据。

### 新增 API 接口

1. 在 `schemas/` 定义 Request/Response Schema。
2. 在 `api/v1/` 新建路由文件。
3. 在 `router.py` 注册路由。
4. 使用 `BaseResponse[T]` 包装响应。
