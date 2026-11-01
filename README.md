# AI Travel Planner

基于多智能体协作的智能旅行规划系统。V1.0 聚焦自然语言需求收集、旅行方案生成、查询、修改、导出和分享；真实预订、支付、订单履约等全流程交易能力只保留架构边界，放到 V2.0 或后续阶段。

仓库地址：<https://github.com/tomo-rrow-cmd/Traval-agent-planner>

## 主要能力

- **对话式规划**：自然语言收集出发地、目的地、天数、预算与偏好，用户明确确认后再启动规划，过程通过 SSE 推送进度。
- **多智能体协作**：LangGraph 主编排 9 个智能体，另有 6 个 Agent/工具模块按需独立调用。
- **真实数据接入**：高德地图与天气、12306 火车票、美团酒旅、BGE-M3 向量检索。
- **方案闭环**：查询、修改、重新生成、收藏、分享；后端导出 Markdown（同步）与 PDF / DOCX（异步任务），Web 端额外支持本地渲染 PNG。
- **行程执行**：签到打卡、每日推进、花费记录、行程调整检测与执行。
- **游记生成**：按行程生成游记与社交素材，支持发布和分享码访问。
- **双端客户端**：Vue 3 Web 与 Kotlin + Jetpack Compose Android。

## 架构概述

```
用户 → API 接口层 → 业务应用服务层 → 编排层 (LangGraph) → 多智能体协作 → 服务能力层 → 外部服务
```

- **API 层**：FastAPI REST/SSE 接口，统一响应封装与异常处理
- **业务应用服务层**：封装用户、对话、方案、行程、游记用例，避免 API 层直接拼装业务结果
- **编排层**：LangGraph 工作流，协调多个智能体顺序/并行执行
- **智能体层**（全部已实现）：UserInteractionAgent（意图识别/参数收集）、AttractionAgent（景点，已接入天气影响因子排序）、FoodAgent（美食）、HotelAgent（住宿）、DecisionAgent（两轮确定性定稿）、DetailAgent（详情扩展）、TrafficAgent（交通，已支持去程/返程火车票）、BudgetAgent（预算核算）、AdjustAgent（超预算参数修正）参与 LangGraph 主编排；TripAgent（行程执行）、TravelogueAgent（游记生成）、PhotoPlannerAgent（看图规划/Vision 提取偏好）、WeatherAgent（天气查询与出行建议）、RouteOptimizerAgent（路线优化）、SouvenirAgent（纪念品）为独立调用 Agent/工具模块
- **服务层**：LLM 适配、地图 API、天气 API（含天气影响因子计算）、向量检索、导出渲染、数据库访问
- **客户端**：Web (Vue 3)、Android (Kotlin + Jetpack Compose)

## 快速开始

环境要求：Python 3.12、Node.js 20.19+（Vite 8 要求）、PostgreSQL；Redis 为可选缓存。

### 方式一：一键启动（推荐）

```bash
python scripts/quickstart.py
```

Windows 用户也可以直接双击仓库根目录的 `quickstart.cmd`：它会自动选用 Python 3.12，结束后保留窗口，不会闪退。

脚本按顺序完成：创建 `.env` → 校验数据库连接与第三方 Key（**已配置且可用则跳过询问**）→ 缺少依赖时自动安装 → 执行 Alembic 迁移 → 启动后端与前端并打开浏览器。

| 参数 | 说明 |
| --- | --- |
| `--force` | 忽略现有配置，强制重新校验并询问所有参数 |
| `--no-frontend` | 只启动后端 |
| `--no-install` | 不自动安装依赖 |
| `--no-reload` | 关闭 uvicorn 热重载 |
| `--no-browser` | 启动后不自动打开浏览器 |

需要准备的输入：PostgreSQL 连接信息、DeepSeek API Key、高德 Web 服务 Key、高德 JSAPI Key（前端地图）。`SECRET_KEY` 缺失时自动生成。

### 方式二：手动启动

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接与第三方 API Key

# 3. 安装前端依赖
npm --prefix frontend install

# 4. 建库建表（需要 psql 在 PATH 中）
python scripts/init_db.py

# 5. 启动后端
./scripts/start_backend.sh            # Linux/macOS
# scripts\start_backend.cmd           # Windows CMD
# .\scripts\start_backend.ps1         # Windows PowerShell

# 6. 启动前端（另开终端）
./scripts/start_frontend.sh
```

`python main.py` 可在 macOS/Linux 上同时拉起前后端；该入口依赖 `os.setsid`，Windows 下请使用 `quickstart.py` 或分开启动。

启动后：

- 前端：<http://localhost:5173>
- 后端 API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>

### Android 客户端（可选）

高德 Key 不写入仓库，构建时通过环境变量注入：

```bash
# macOS / Linux
export AMAP_KEY="<你的高德Key>"

# Windows PowerShell
$env:AMAP_KEY="<你的高德Key>"
```

也可以写入 `android/local.properties`（已被 `.gitignore` 忽略）：`AMAP_KEY=<你的高德Key>`。然后用 Android Studio 打开 `android/` 构建；未配置 Key 时构建仍可完成，仅地图相关页面不可用。

启动脚本会自动选择可用运行器：指定 `--python` / `BACKEND_PYTHON` 时优先使用它；否则依次尝试当前 Python、项目 `.venv`、conda 环境、`uv run --with-requirements requirements.txt`，最后退回系统 `python` / `python3` / Windows `py` 并提示缺失依赖。

默认配置读取 `.env`，示例见 `.env.example`。如配置 `MEITUAN_TOKEN`，服务启动时会自动写入 `~/.config/meituan-travel/config.json` 的 `key` 字段，供 `mttravel` CLI 读取。本地服务入口为 `main.py`，FastAPI 应用注册在 `app.api.router:app`。

## 项目结构

```
.
├── .agent/                     # 架构约束、编码规范、决策记录与 AI 禁飞区
├── .coveragerc                 # 覆盖率统计配置
├── .dockerignore
├── .env.example                # 环境变量示例
├── .gitlab-ci.yml              # GitLab CI 流水线（validate → test → build → deploy）
├── Dockerfile                  # python:3.12-slim 运行镜像
├── alembic.ini
├── main.py                     # 一键启动前端 Vite 与后端 uvicorn
├── pytest.ini
├── requirements.txt
│
├── app/                        # FastAPI 后端
│   ├── api/
│   │   ├── router.py           # 应用装配、CORS、静态目录、全局异常处理
│   │   └── v1/                 # auth / chat / plan / trip / travelogue / user / data / ops
│   ├── agents/
│   │   ├── base.py / context.py
│   │   ├── user_interaction_agent.py / attraction_agent.py / food_agent.py
│   │   ├── hotel_agent.py / detail_agent.py / traffic_agent.py
│   │   ├── budget_agent.py / adjust_agent.py / decision_agent.py
│   │   ├── trip_agent.py / travelogue_agent.py / photo_planner_agent.py
│   │   ├── weather_agent.py / route_optimizer_agent.py / souvenir_agent.py
│   │   └── tools/              # tool_registry + attraction / budget / map / weather 工具
│   ├── core/                   # security.py：JWT、密码哈希
│   ├── db/
│   │   ├── models/             # 15 张业务表
│   │   ├── repositories/       # 9 个数据访问封装
│   │   ├── migrations/         # Alembic 环境与 versions/ 迁移脚本
│   │   └── session.py
│   ├── orchestrator/           # graph / nodes / pipeline / state / conflict_detection
│   ├── schemas/                # Pydantic 请求响应模型
│   ├── services/
│   │   ├── application/        # 用户、对话、方案、游记、行程应用服务
│   │   ├── data/               # 景点、餐厅、酒店基础数据服务
│   │   ├── export/             # Markdown / DOCX / PDF 渲染与临时导出任务
│   │   ├── llm/                # DeepSeek / 豆包 / 通义千问适配 + Vision
│   │   ├── map/                # 高德地图与地理编码适配
│   │   ├── third_party/        # 美团酒旅、12306、实时 POI
│   │   ├── vector/             # BGE-M3 embedding、Chroma、RAG、reranker
│   │   └── weather/            # 高德天气适配 + 天气影响因子
│   └── utils/                  # cache / pipeline_cache / logger / validator
│
├── android/                    # Kotlin + Jetpack Compose 客户端
│   ├── app/
│   │   ├── build.gradle.kts    # compileSdk 34 / minSdk 26 / Compose + Hilt + Retrofit + Room
│   │   └── src/main/java/com/travel/planner/
│   │       ├── data/           # remote(Retrofit/SSE)、repository、local(DataStore)
│   │       ├── domain/         # model 与 repository 接口
│   │       ├── di/             # Hilt 模块
│   │       └── presentation/   # navigation、theme、screens(auth/chat/home/plan/trip/travelogue)
│   ├── gradle/wrapper/
│   └── settings.gradle.kts
│
├── docs/                       # 项目文档
│   ├── README.md               # 文档总入口
│   ├── architecture/           # 架构主文档 + chapters / backend / database / diagrams /
│   │                           # implementation / snapshots
│   ├── api/                    # API 接口规范
│   ├── android/                # Android 开发规范
│   ├── CI-CD/                  # 流水线说明
│   ├── decisions/              # 架构决策记录（ADR 01–05）
│   ├── front-docs/             # 前端设计、视觉系统与测试报告
│   ├── requirements/           # 需求设计说明书
│   ├── planning/               # 优先级与任务清单
│   ├── need_fix/               # 问题定位与修复方案
│   ├── originals/              # Word / Excel 原始设计稿
│   ├── Sprint1/  Sprint2/      # 阶段验收、质量门禁与测试材料
│   ├── assets/                 # 文档引用图片
│   └── reports/                # ai-logs / CMJ / FYW / TBY 日报周报 / 团队报告
│
├── frontend/                   # Vue 3 + TypeScript Web 客户端
│   ├── src/
│   │   ├── api/                # 11 个接口封装模块
│   │   ├── components/         # 50 个组件，按 auth/chat/plan/trip/common 等分包
│   │   ├── views/              # 13 个页面
│   │   ├── store/              # Pinia：auth / chat / plan / trip / travelogue / preference / ui
│   │   ├── router/ types/ utils/ styles/
│   │   ├── standalone/         # 独立城市选择器与 cities.json
│   │   └── test/               # Vitest 用例与 mock
│   ├── public/
│   └── package.json / vite.config.ts / vitest.config.ts
│
├── scripts/                    # 初始化、启动与调试脚本
│   ├── start_backend.sh / start_backend.ps1 / start_backend.cmd
│   ├── start_frontend.sh
│   ├── init_db.py              # 建库与 Alembic 迁移
│   ├── rebuild_vectors.py      # 全量重建向量索引
│   ├── seed_poi.py             # 按城市拉取并写入 POI
│   ├── seed_travelogues.py     # 游记示例数据
│   ├── replace_test_data.py
│   ├── test_agent.py / test_agents.py
│   ├── test_pipeline.py / test_orchestration.py
│   ├── test_full_pipeline.py / test_v2_execution.py
│   └── ...
│
└── tests/                      # 52 个测试模块（agents / api / services / rag / export 等）
```

## 多智能体编排流程

### 主编排图（LangGraph）

```text
用户消息 → UserInteractionAgent（意图识别/参数收集）
  ├─ 信息不足或未确认 → SSE 回复并返回 waiting_input
  └─ 用户明确确认 → LangGraph
       → [并行] AttractionAgent + FoodAgent + HotelAgent
       → DecisionAgent R1（定稿景点和餐厅，每日最多 4 个景点）
       → DetailAgent（补充重点景点和餐厅详情，美团/高德）
       → DecisionAgent R2（按通勤评分选择最优酒店）
       → TrafficAgent（大交通 12306 + 市内路线高德）
       → BudgetAgent（预算核算 + 最终方案）
       ├─ 未超预算 → 输出 final_plan
       └─ 超预算（≤30% 且 retry<2）→ AdjustAgent 修正参数 → 回到并行阶段重跑
```

### 独立调用 Agent（不经过 LangGraph）

| Agent / 模块 | 用途 | 调用方 |
|-------|------|--------|
| TripAgent | 行程执行：签到、进度、每日提醒、预算追踪 | `app/api/v1/trip.py` |
| TravelogueAgent | 游记生成、照片整理、社交素材 | `app/api/v1/travelogue.py` |
| PhotoPlannerAgent | 上传照片 → Vision 提取偏好 → 生成方案 | 独立 Agent / UserInteractionAgent 前序 |
| WeatherAgent | 天气查询与出行建议 | 独立服务调用 |
| RouteOptimizerAgent | TSP/VRP 路径优化 | 独立工具模块 |
| SouvenirAgent | 纪念品推荐 | 独立 Agent |
| ConflictDetector | 时间/位置/预算/营业时间冲突检测 | `app/orchestrator/` |

规划进度通过 LangGraph 节点更新转成 SSE `progress` 事件。完成结果写入 PostgreSQL 的
`conversation_plan_runs`，同一会话每次生成新增一个 `sequence` 版本；`conversations.plan_id`
指向最新版本。结构化方案只保存在 `conversation_plan_runs.summary`；`plan_result` 消息保存
Markdown 和 `plan_run_id`，历史 API 读取时动态补充 summary。聊天消息保存在 `messages`，
会话标题和置顶状态保存在 `conversations`。长期可编辑、分享和收藏的正式方案模型仍由独立的
`plans` 表承载，两种记录不要混用。

## 技术栈

| 层次 | 技术选型 |
|---|---|
| 后端 | Python 3.12、FastAPI 0.115、SQLAlchemy 2 (async)、Alembic、Redis |
| 数据库 | PostgreSQL |
| 编排 | LangGraph 0.2 |
| LLM | OpenAI 兼容 SDK：DeepSeek / 豆包 / 通义千问，含 Vision 图片识别 |
| RAG | Chroma 1.5.9 + BGE-M3（1024 维）+ BGE reranker |
| 地图 / 天气 | 高德 Web 服务（地图、地理编码、天气） |
| 导出 | Markdown、python-docx、WeasyPrint / fpdf2、Pillow |
| 前端 | Vue 3.5、TypeScript 6、Vite 8、Pinia 3、Vue Router 5、Ant Design Vue 4、Vitest 4 |
| 客户端 | Kotlin + Jetpack Compose（BOM 2025.02）、Hilt、Retrofit、Room、DataStore、高德 3D 地图 |

## API 概览

所有业务接口挂载在 `/api/v1` 下，详细契约见 [API 规范](docs/api/API接口规范文档.md)。

| 领域 | 路径 |
|------|------|
| 认证 | `POST /api/v1/auth/register`、`POST /api/v1/auth/sms-codes`、`POST /api/v1/auth/sessions`、`POST /api/v1/auth/tokens`、`DELETE /api/v1/auth/sessions/current` |
| 用户 | `GET/PUT /api/v1/user/profile`、`GET/PUT /api/v1/user/preferences`、`POST /api/v1/user/sessions/anonymous/merge` |
| 对话 | `POST/GET /api/v1/chat/sessions`、`PATCH/DELETE /api/v1/chat/sessions/{sessionId}`、`POST/GET /api/v1/chat/sessions/{sessionId}/messages`、`GET /api/v1/chat/sessions/{sessionId}/stream`、`GET /api/v1/chat/sessions/{sessionId}/plans`、`POST /api/v1/chat/upload/image` |
| 方案 | `GET/POST /api/v1/plans`、`GET/PATCH/DELETE /api/v1/plans/{planId}`、`POST /api/v1/plans/{planId}/generations`、`POST /api/v1/plans/{planId}/exports`、`POST /api/v1/plans/{planId}/shares`、`POST /api/v1/plans/{planId}/favorites`、`POST /api/v1/plans/{planId}/save`、`POST /api/v1/plans/from-data` |
| 行程 | `GET/POST /api/v1/trips`、`GET/PATCH /api/v1/trips/{tripId}`、`POST /api/v1/trips/{tripId}/advance-day`、`GET /api/v1/trips/{tripId}/progress`、`POST/GET /api/v1/trips/{tripId}/checkins`、`POST/GET /api/v1/trips/{tripId}/expenses`、`POST /api/v1/trips/{tripId}/adjustments/detect`、`GET /api/v1/trips/{tripId}/adjustments`、`POST /api/v1/trips/{tripId}/adjustments/{adjId}/accept\|reject\|apply`、`GET /api/v1/trips/{tripId}/reminder`、`POST /api/v1/trips/{tripId}/photos/annotate` |
| 游记 | `GET/POST /api/v1/travelogues`、`GET /api/v1/travelogues/by-trip/{tripId}`、`GET/PATCH/DELETE /api/v1/travelogues/{id}`、`POST /api/v1/travelogues/{id}/publish`、`POST /api/v1/travelogues/{id}/regenerate`、`POST /api/v1/travelogues/materials/generate`、`GET /api/v1/travelogues/materials`、`POST /api/v1/travelogues/materials/{materialId}/favorite`、`POST /api/v1/travelogues/shares`、`GET /api/v1/travelogues/shares/{shareCode}` |
| 基础数据 | `GET /api/v1/data/cities`、`GET /api/v1/data/attractions`、`GET /api/v1/data/attractions/{id}`、`GET /api/v1/data/restaurants`、`GET /api/v1/data/hotels`、`GET /api/v1/data/weather` |
| 运维 | `GET /api/v1/health`、`GET /api/v1/tasks/{taskId}`、`GET /api/v1/tasks/{taskId}/download` |

统一响应和错误处理：

- JSON 成功响应统一为 `{ code, message, data, request_id }`。
- 分页响应统一使用 `list/total/page/page_size/total_pages`。
- 请求参数校验错误返回 HTTP 400 + 业务码 `10001`；未授权返回 HTTP 401 + 业务码 `20001`；资源不存在返回 HTTP 404 + 业务码 `10003`。
- SSE 接口返回 `text/event-stream`，事件类型包括 `message_delta`、`message`、`step_start`、`progress`、`step_end`、`done`、`error`。

对话 Agent 会区分普通闲聊和旅行规划意图。旅行规划在收齐出发地、目的地、天数、总预算和偏好后，先返回确认话术；只有用户明确确认，后端才启动 LangGraph 规划。预算字段同时保留 `total_budget`、`reserve_budget` 和 `planning_budget`，用于区分总预算、应急预留和本次实际规划额度。

方案导出：`md` 由后端同步返回文件流；`docx`、`pdf` 创建后台任务，通过 `/api/v1/tasks/{taskId}` 查询状态并从 `/download` 下载。`image`（PNG）由 Web 端用 html2canvas / jsPDF 在浏览器内渲染，不经过后端导出任务。

## RAG 与 Chroma 维护

RAG 默认使用 `BAAI/bge-m3` 生成 1024 维向量，并用 `BAAI/bge-reranker-base` 对 `RAG_TOP_K` 候选重排到 `RAG_FINAL_K`。如果从旧 embedding 模型切换过来，需要重新运行 `scripts/seed_poi.py --city 城市名` 重建 Chroma collection，否则旧 512 维向量会和新查询向量维度不匹配。

本地嵌入式 Chroma 只允许一个后端、灌数或重建进程持有 `chroma_data`。维护前必须停止后端；如果目录仍被占用，命令会在修改 PostgreSQL 或索引前退出。

- 全量恢复或模型切换：`python scripts/rebuild_vectors.py`
- 刷新某个城市的数据：`python scripts/seed_poi.py --city 北京`
- 不再支持 `rebuild_vectors.py --city`；城市刷新完成后会从 PostgreSQL 全量构建影子索引。

重建先写入 `.chroma_data.rebuild-*`，数量和样例查询全部通过后才切换为活动目录。原索引保留为 `chroma_data.backup-<timestamp>`，重建失败时活动索引保持不变。启动时如果现有 HNSW 无法读取，后端会拒绝启动并提示执行全量重建；首次运行且没有任何 collection 时允许降级启动。

## 测试

推荐使用项目 conda 环境执行验证：

```bash
conda run --no-capture-output -n ai-travel-planning python -m pytest -m "not integration" tests
python -m compileall app tests
git diff --check
```

`tests/` 下共 52 个测试模块，默认测试集为离线门禁，不依赖真实 PostgreSQL/Redis、第三方 API、LLM API Key、向量库数据或 runner 本机服务状态。需要真实数据库、第三方 API、LLM、向量检索、POI 拉取或完整 Agent 编排的用例使用 `@pytest.mark.integration` 标记，默认 CI 会跳过。

```bash
# 集成测试（需先准备外部资源）
conda run --no-capture-output -n ai-travel-planning python -m pytest -m "integration" tests
```

前端测试：

```bash
npm --prefix frontend run test
```

## CI/CD

流水线配置位于 `.gitlab-ci.yml`，分为四个阶段：

- **validate**：`compile`（Python 语法编译）、`frontend:lint`（ESLint）、`frontend:typecheck`（vue-tsc）。
- **test**：`pytest`（`-m "not integration"`，覆盖率门禁 84%）、`frontend:test`（Vitest）。
- **build**：`frontend:build`（vite build）、`docker_image`（手动，仅 `dev` 分支和 tag）。
- **deploy**：`deploy_staging`（手动占位任务）。

> 说明：当前代码托管在 GitHub，`.gitlab-ci.yml` 保留为原 CI 配置；如需在 GitHub 上自动执行，需要迁移为 GitHub Actions 或接入自建 GitLab Runner。

当前 CI 适配 GitLab shell runner。Runner 需要：

- 注册 executor 为 `shell`。
- tag 包含 `shell`，与 `.gitlab-ci.yml` 的默认 tag 匹配。
- runner 所在机器能执行 `conda run -n ai-travel-planning python --version`。
- runner 所在机器需要 Node.js 20.19+（Vite 8 要求；脚本内最低校验为 18），推荐通过 nvm 安装。
- user-mode runner 需要保持 `gitlab-runner run` 进程运行；终端关闭或机器离线会导致 job pending/stuck。

容器运行入口为：

```bash
uvicorn app.api.router:app --host 0.0.0.0 --port 8000
```

生产、测试或集成测试环境需要通过 CI/CD Variables 注入 `SECRET_KEY`、`DATABASE_URL`、`REDIS_URL` 以及第三方服务 Key。默认离线 CI 不需要真实第三方 API Key 或 LLM API Key。不要把真实密钥写入仓库。

## 已知限制

- 短信验证码为开发态 mock（固定 `123456`），未接入真实短信服务与发送频率限制。
- 真实预订、支付、订单履约未实现，仅保留架构边界。
- SSE 不支持断点续传，连接中断后需重新发起。
- 嵌入式 Chroma 为单进程独占，后端运行时不能并行执行灌数或重建。
- 天气服务类名 `QWeatherService` 为历史命名，实际调用的是高德天气接口。

## 文档与协作

- 项目文档入口：[docs/README.md](docs/README.md)
- 架构文档入口：[docs/architecture/README.md](docs/architecture/README.md)
- 多智能体协作旅行规划架构：[docs/architecture/multi-agent-collaboration.md](docs/architecture/multi-agent-collaboration.md)
- 后端实现架构快照：[docs/architecture/backend/README.md](docs/architecture/backend/README.md)
- 当前代码结构快照：[docs/architecture/snapshots/code-structure.md](docs/architecture/snapshots/code-structure.md)
- API 规范：[docs/api/API接口规范文档.md](docs/api/API接口规范文档.md)
- 数据库设计：[docs/architecture/database/数据库设计文档.md](docs/architecture/database/数据库设计文档.md)
- Android 开发规范：[docs/android/Android客户端开发规范.md](docs/android/Android客户端开发规范.md)
- 架构设计说明书（产品视角）：[docs/architecture/架构设计说明书.md](docs/architecture/架构设计说明书.md)
- 软件架构设计文档（技术基线）：[docs/architecture/软件架构设计文档.md](docs/architecture/软件架构设计文档.md)
- 架构配图源文件：[docs/architecture/diagrams/](docs/architecture/diagrams/)
- 智能体协作约束：`.agent/architecture.md`、`.agent/conventions.md`、`.agent/decisions.md`、`.agent/guardrails.md`（AI 禁飞区）

开发前先阅读 `.agent` 目录中的架构约束、编码规范和决策记录。当前仓库采用后端根目录 `app/` 的模块化单体结构；不要在未确认的情况下新增顶层业务目录、迁移目录、重命名模块或改变入口文件。
