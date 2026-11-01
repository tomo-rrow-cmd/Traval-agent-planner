# AI旅行规划师编码与协作规范

本文件约束本仓库的日常编码、接口、测试、提交和分支协作。若本文件与 `docs/originals/AI旅行规划师技术架构设计文档.docx` 存在冲突，以 `.agent/decisions.md` 中的显式决策为准。

## 1. 通用工程规范

- 代码优先保持简单、可测试、可替换；不要为了未来微服务化提前引入复杂基础设施。
- 所有配置通过环境变量或配置文件注入，不得硬编码密钥、Token、数据库连接串、第三方服务 Key。
- 外部依赖必须封装在服务层或适配器中；业务逻辑、智能体和 API 层不得直接散落调用第三方 SDK。
- 精确计算类逻辑使用确定性算法实现，例如路线优化、预算统计、时间校验、距离计算；不要交给 LLM 直接“算”。
- LLM 适用于自然语言理解、内容生成、推荐理由、结果润色、结构化抽取和排序辅助。
- 默认时区使用 `Asia/Shanghai`；数据库持久化时间字段按 `docs/architecture/database/数据库设计文档.md` 使用 UTC 存储，对外 API 的日期时间使用 ISO 8601 格式并带时区。
- 所有用户输入、LLM 输出、第三方 API 返回值进入核心流程前必须做结构校验。
- 不提交 `.env`、本地数据库、日志、缓存、构建产物、IDE 私有配置和真实密钥。
- 请不要轻易调整现有文件结构，如需修改，请先和用户沟通，不要擅自修改。
- 当前代码结构以 `docs/architecture/snapshots/code-structure.md` 的“当前代码结构快照”为准；该快照只记录纳入版本管理的源文件、脚本和文档，不记录 `__pycache__/`、`builds/`、`cache/`、`chroma_data/` 等本地产物。新增目录、迁移目录、重命名模块或调整入口文件前，必须先说明影响范围并获得用户确认。如果已经确认要更改文件结构，请及时更新文件结构快照。
- 架构文档目录采用 `docs/architecture/README.md` 作为入口；拆分章节放在 `docs/architecture/chapters/`，数据库表结构专题放在 `docs/architecture/database/`，原始 Office 文件保留在 `docs/originals/`。
- 当前仓库事实基线为前后端单仓：后端模块化单体入口在 `app/`，Web 客户端在 `frontend/`，Android 客户端在 `android/`，文档在 `docs/`，脚本在 `scripts/`，测试在 `tests/`；如需新增顶层业务目录，先确认目录方案。
- 后端本地启动脚本统一维护在 `scripts/start_backend.sh`、`scripts/start_backend.ps1` 和 `scripts/start_backend.cmd`。修改启动参数、运行器选择、数据库检查、向量重建或 uvicorn 参数时，需要保持三端行为一致，并同步更新 README、`.agent/decisions.md` 和代码结构快照。启动脚本不得硬编码密钥，也不得默认执行建库、写业务数据、重建 Chroma 或下载大模型。

## 2. 后端编码规范

默认后端技术栈为 Python + FastAPI + Pydantic + SQLAlchemy 2.0 async。

- 遵循 PEP 8，缩进使用 4 个空格，单行最长 120 字符。
- 所有公共函数、方法、类属性和复杂数据结构必须写类型注解。
- API 入参和出参必须使用 Pydantic Schema，不直接透出 ORM Model。
- 数据库访问统一走 Repository/DAO 或服务层封装，不在 API 层直接查询数据库。
- I/O 密集逻辑使用 `async/await`；不要在异步请求链路中调用阻塞式网络或数据库客户端。
- SQLAlchemy 查询优先使用 ORM/表达式 API，禁止拼接 SQL 字符串。
- 数据库结构变更必须配套迁移脚本，避免只改 Model 不改迁移。
- 公共类和公共方法使用 Google 风格 docstring；行内注释只解释非显而易见的业务原因。
- TODO 必须写清负责人或 Issue、待办内容和完成条件，例如 `TODO(#12): 补充酒店价格数据源`。

### 后端命名

- 类名：`PascalCase`，例如 `TravelPlanService`
- 函数/变量：`snake_case`，例如 `get_user_profile`
- 常量：`UPPER_SNAKE_CASE`，例如 `MAX_RETRY_COUNT`
- 数据库表：复数 `snake_case`，例如 `travel_plans`
- 数据库字段：`snake_case`，例如 `created_at`
- API 路径：小写复数资源名 + 连字符，例如 `/api/v1/plans`

## 3. 前端编码规范

默认前端技术栈为 Vue 3 + Vite + TypeScript + Ant Design Vue + Pinia + Vue Router。

- 使用 Vue 3 Composition API；组件内逻辑按状态、计算、请求、事件处理分组。
- 组件文件使用 `PascalCase.vue`，例如 `PlanDetail.vue`。
- 变量和函数使用 `camelCase`，类型和接口使用 `PascalCase`。
- API 请求必须集中封装在 `src/api/`，页面组件不得直接散落写 `fetch`/`axios` 调用。
- 所有后端响应类型必须在 `src/types/` 或同等类型目录中定义。
- CSS class 推荐 BEM 命名；优先复用组件库和项目内通用组件。
- 使用 ESLint + Prettier 统一格式；提交前应通过 lint 和类型检查。

## 4. Android 编码规范

Android 客户端编码规范详见 [docs/android/Android客户端开发规范.md](../docs/android/Android客户端开发规范.md)。核心技术栈为 Kotlin + Jetpack Compose，采用 MVVM + Repository 分层架构。以下为通用原则：

- 使用 Kotlin 协程处理异步逻辑；ViewModel 使用 `viewModelScope`，不可在 ViewModel 中直接启动全局协程。
- 网络请求统一走 Retrofit + OkHttp，API 接口集中在 `data/remote/api/`，不得在 UI 层散落 HTTP 调用。
- 数据模型分为 DTO（网络传输）、Domain Model（业务实体）两层，Repository 负责 DTO ↔ Domain 转换。
- 依赖注入使用手动 DI（`di/` 模块），暂不引入 Hilt/Koin 框架。
- API 响应类型必须与后端契约对齐，SSE 流解析统一走 `SseClient` 封装。
- 主题色、字体、形状等设计 Token 集中定义在 `presentation/theme/`。

## 5. API 规范

- API 使用 RESTful 风格，版本前缀固定为 `/api/v1/`；详细接口定义以 `docs/api/API接口规范文档.md` 为准。
- 当前源码执行 API 契约 MVP：公开路径以 `docs/api/API接口规范文档.md` 为准，旧路径 `/conversations`、`/travel-plans`、`/users/me` 和根路径 `/health` 不再保留。
- 当前认证路径包括 `POST /auth/register`、`POST /auth/sms-codes`、`POST /auth/sessions`、`POST /auth/tokens`、`DELETE /auth/sessions/current`；开发态短信验证码固定为 `123456`，生产接入真实短信和限流前不得宣称完成生产级认证。
- 资源路径使用名词复数，不使用动词路径；动作类能力优先建模为资源或子资源。
- HTTP 方法语义：
  - `GET`：查询
  - `POST`：创建或触发非幂等任务
  - `PUT`/`PATCH`：更新
  - `DELETE`：删除或软删除
- 列表接口统一支持 `page`、`page_size`、`sort_by`、`sort_order` 和必要筛选参数；`page` 从 1 开始，`page_size` 默认 20，最大 100。
- 耗时任务，例如完整旅行方案生成，优先使用异步任务或 SSE 流式输出。
- 当前 SSE 接口包括 `POST /chat/sessions/{sessionId}/messages`、`GET /chat/sessions/{sessionId}/stream`、`POST /plans`、`PATCH /plans/{planId}`、`POST /plans/{planId}/generations`。事件类型统一为：`message_delta`、`message`、`progress`、`step_start`、`step_end`、`done`、`error`。对话流可先发送 `message_delta` 增量，再发送完整 `message` 供持久化和前端兜底展示；契约 MVP 阶段允许使用 deterministic stub 事件流验证前后端协议，接入真实编排后必须保持事件名和字段兼容。
- 方案生成必须有显式确认门控：`POST /plans` 和 `POST /plans/{planId}/generations` 请求体使用 `confirmed` 表示用户已经确认参数；未确认时只返回等待确认的 SSE 消息，不进入 LangGraph 规划。对话消息流也必须在 `mode=travel_planning`、`ready=true` 且 `confirmed=true` 时才启动完整规划。
- 同一对话会话中可生成多份方案，历史方案摘要通过 `GET /chat/sessions/{sessionId}/plans` 返回，并由 `conversation_plan_runs` 表持久化；对话 Agent 读取最近一次方案上下文时，不得把普通闲聊误判为自动重规划。
- 分页响应字段使用 `list`、`total`、`page`、`page_size`、`total_pages`，不得再对外返回旧的 `items` 字段。
- FastAPI/Starlette 默认错误不得直接透出给前端；请求校验错误应转换为 HTTP 400 + 业务码 `10001`，未授权为 HTTP 401 + `20001`，资源不存在为 HTTP 404 + `10003`。业务错误码不得当作 HTTP status 使用。
- `POST /plans/{planId}/exports?format=md` 同步返回 Markdown 文件；`pdf/image/docx` 创建进程内临时任务，通过 `GET /tasks/{taskId}` 查询并从 `GET /tasks/{taskId}/download` 下载。不支持的格式返回业务码 `40006`。临时任务按用户隔离、完成后保留 1 小时且不保证跨进程重启恢复。
- API 测试必须覆盖新路径、旧路径 404、统一响应字段、分页与双向游标、SSE content-type/事件名、资源归属、方案结果原子持久化、mock auth、基础数据、任务状态和任务下载。
- 错误响应不得暴露堆栈、SQL、密钥、供应商原始错误等内部细节；内部细节进入日志。

推荐统一响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_xxx"
}
```

## 6. 数据与缓存规范

- PostgreSQL 存储用户、会话、消息、会话方案版本、正式方案和 POI 等结构化业务数据；Redis 能力目前仅为配置/架构预留，不得描述为已接入的会话或锁实现。
- 业务表结构、字段和索引以 `docs/architecture/database/数据库设计文档.md` 为准；删除恢复能力需要显式设计软删除，不作为默认删除口径。
- 对话会话内的多次方案生成结果写入 `conversation_plan_runs`，只保存面向会话上下文和列表展示的方案摘要；长期可编辑/分享的正式方案仍以 `plans` 表和方案服务为主。
- 重要业务表可预留 `extra`/`metadata` JSONB 字段，但不得用 JSONB 替代核心可查询字段。
- 所有写操作应具备幂等设计；重复请求不能产生重复方案、重复订单或重复扣费。
- 缓存采用 Cache Aside：读时先缓存，未命中查库并回填；写时先写库再失效缓存。
- Redis Key 使用 `业务域:数据类型:唯一标识`，例如 `plan:session:abc123`、`weather:forecast:430100`。
- 同一会话并发规划需要在后续实现任务锁；当前代码尚未使用 Redis 分布式锁，调用方应避免对同一 session 并发触发完整规划。

## 7. Agent 与 LLM 规范

- 智能体必须通过统一基类（`BaseAgent`）接入编排层，不允许绕过 LangGraph 编排图直接互相调用。
- 智能体之间通过 LangGraph `PlannerState`（`app/orchestrator/state.py`）共享状态；编排图节点负责读取上游字段并写入自身负责的字段，Agent 本身不直接读写 State。
- 规划进度通过 LangGraph 节点更新转为 SSE `progress` 事件推送给前端。
- 每个编排节点只能写入自己负责的 State 字段；读取其他字段时不得隐式修改。
- Agent 输出写入 State 前必须经过 Pydantic Schema 校验（`app/schemas/agent_outputs.py`）。
- Prompt 独立存储、版本化管理，不硬编码在业务函数中。
- LLM 调用统一经过 LLM 服务层；当前主模型适配器为 DeepSeek，豆包和通义千问保留为备选适配器。业务模块和 Agent 不直接调用模型 SDK。
- 对话 Agent 支持流式输出时，应只把用户可见内容作为 `message_delta` 发送；内部就绪哨兵值（例如 `READY`）不得直接透出给前端。
- 对话 Agent 必须先识别 `daily_chat` 与 `travel_planning`，收齐出发地、目的地、天数、预算和偏好后进入 `awaiting_confirmation`，用户明确确认后才返回 `confirmed=true` 和 `ready=true`。已完成方案的会话继续闲聊时默认不沿用旧方案，只有用户明确要求重新规划、沿用配置或修改目的地时才开启新一轮规划。
- 预算 Agent 输出需要同时保留 `total_budget`、`reserve_budget` 和 `planning_budget`，避免把应急预留计入实际可安排额度；最终方案摘要应携带 `trip_config`，供同会话后续重规划继承上下文。
- Agent 可用工具通过 `app/agents/tools/tool_registry.py` 注册。景点、餐厅、酒店、天气、路线、美团酒旅、12306 等能力必须通过工具注册表或服务适配器调用，不在 Agent 中散落外部协议细节。
- RAG 检索链路统一通过 `app/services/vector/rag.py` 暴露的 `rag_search` 进入，流程为 embedding → Chroma Top-K 召回 → reranker 重排 → final K；Agent 和工具注册表不得重复手写 Chroma 结果解析逻辑。
- 第三方 API 或 LLM 失败时最多自动重试 3 次；重试失败后返回可解释的降级结果。美团 CLI 未安装、Token 缺失、BGE 模型未缓存、Chroma 空数据、12306 网络失败等都必须可降级。

## 8. 日志、安全与隐私

- 日志使用结构化 JSON，至少包含时间、级别、模块、请求 ID、用户 ID 或匿名会话 ID、事件内容。
- 不记录密码、验证码、Token、身份证号、完整手机号、支付信息和第三方密钥。
- 错误日志需要保留可定位问题的上下文与完整堆栈，但不得把堆栈、SQL、密钥或第三方原始错误返回给前端或写入用户可见内容。
- 所有外部输入使用 Pydantic 或前端表单规则校验；后端校验是最终可信边界。
- 用户只能访问自己的数据；运营和管理员能力必须通过 RBAC 控制。
- AI 输入和输出都需要预留内容安全审核点；分享、评论、头像昵称等 UGC 不得绕过审核。

## 9. 测试规范

- 核心业务逻辑、算法逻辑、数据校验、智能体关键流程必须有单元测试。
- 第三方 API、LLM、短信、地图、天气等外部调用在单元测试中必须 Mock。
- 默认 CI 测试必须是离线可复现的，不依赖真实 PostgreSQL/Redis、第三方 API、LLM API Key、向量库数据或 runner 本机服务状态。
- 前端测试（Vitest + happy-dom）纳入 CI `test` 阶段，同样不依赖真实后端服务。
- 需要真实数据库、第三方 API、LLM、向量检索、POI 拉取或跨服务编排的用例必须标记 `@pytest.mark.integration`，默认 CI 使用 `pytest -m "not integration" tests` 跳过。
- API/SSE 契约测试可以使用本地 stub 或 monkeypatch 验证 wire shape；不要为了契约测试触发真实 Agent 编排、外部网络请求或真实密钥读取。
- 方案生成、用户登录、方案查看/导出等主流程应有集成测试或端到端测试。
- 核心代码覆盖率目标不低于 84%（与 CI `--cov-fail-under=84` 一致）；低于目标时需要在 MR 中说明原因。
- 修复 bug 必须补充能复现问题的测试，除非该 bug 无法稳定自动化复现。
- shell executor 的 GitLab Runner 会在仓库目录下生成 `builds/`、`cache/` 等本地产物；这些目录不得提交，也不得被 pytest 递归收集。

## 10. Git 分支规范

采用轻量分支策略：

- `main`：稳定分支，只保存可发布代码。
- `dev`：开发集成分支，功能合并后进入该分支。
- `feature/*`：功能分支，从 `dev` 拉出，完成后合并回 `dev`。

推荐分支命名：

- `feature/12-route-agent`
- `feature/34-plan-export`
- `feature/56-auth-login`

约束：

- 不直接向 `main` 推送开发提交。
- 功能开发从 `dev` 创建分支，合并前同步最新 `dev`。
- 仅包含文档、注释、结构快照或协作规范的维护类改动，可在当前分支直接提交；如果当前分支是 `main`，提交前需确认不包含业务代码改动。
- 合并到 `dev` 或 `main` 走 Merge Request/Pull Request；如有对应 Issue，必须在 MR/PR 和提交信息中关联。
- 合并前必须通过 lint、测试和必要的人工 Review。

## 11. Commit 规范

Commit 格式：

```text
<type>: <简述>
<type>: <简述> #<Issue编号>
```

有对应 Issue 时必须使用第二种格式；确实没有 Issue 的小范围文档、配置或整理类提交允许使用第一种格式，但提交说明必须清晰表达变更目的。

允许的 `type`：

- `feat`：新增功能
- `fix`：缺陷修复
- `docs`：文档变更
- `refactor`：不改变行为的重构

示例：

```text
feat: 新增路线优化智能体 #12
fix: 修复方案生成进度中断 #18
docs: 补充Agent架构边界说明 #21
refactor: 拆分天气服务适配器 #27
docs: 更新文件结构快照
```

若一次提交只是关联但不关闭 Issue，使用 `Refs #12` 写在提交正文；若合并后关闭 Issue，使用平台支持的 `Closes #12`。
