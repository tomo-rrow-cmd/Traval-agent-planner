# 数据、API 与第三方集成边界

本文件记录数据存储、第三方适配、API 契约 MVP、RAG 与外部数据源边界。

## 1. 数据架构

核心存储职责：

- PostgreSQL：用户、会话、旅行方案、景点、餐厅、酒店、城市、纪念品、操作日志等结构化数据。
- Redis：会话状态、热点数据缓存、限流计数、分布式锁。
- 向量数据库：景点/美食/知识库语义检索。V1.0 可使用 Chroma，规模增长后迁移 Milvus。
- 对象存储：图片、导出文件、方案附件等非结构化对象。

数据流原则：

- 数据从底层向上层单向流动，上层不直接越级操作底层。
- 数据访问通过服务封装，不能在多个模块重复拼装查询逻辑。
- 基础数据需要清洗、标准化、去重、校验后再入库。
- 缓存与数据库允许短暂最终一致，核心写操作使用事务保证一致性。

## 2. 第三方服务边界

第三方服务必须通过适配器封装：

- 地图服务：高德地图为主，百度地图可作为备选。
- 天气服务：当前代码的 `app/services/weather/qweather.py` 使用高德天气接口和 `AMAP_API_KEY`；历史架构中的和风天气/心知天气仍作为可替换供应商口径，不直接散落调用。
- LLM 服务：当前代码以 DeepSeek 为主模型，豆包和通义千问作为备选适配器，均通过统一 LLM 接口调用。
- 酒旅/票务数据：美团酒旅 CLI、12306 查询等放在 `services/third_party/`，只能作为数据源/查询适配器，不进入 V1.0 真实预订、支付和履约。
- 内容安全：用户输入、分享内容和 AI 输出预留审核接口。

适配器必须处理：

- 超时、重试、熔断和降级。
- 供应商错误码到内部错误码的转换。
- 请求日志和响应摘要，敏感字段脱敏。
- 缓存策略和配额保护。

## 3. API 与交互边界

核心 API 领域：

- 认证接口：登录、刷新 Token、登出。
- 用户接口：用户资料、偏好配置。
- 对话接口：会话创建、消息发送、历史查询、流式回复。
- 方案接口：生成、查询、修改、导出、分享。
- 基础数据接口：城市、景点、餐厅、酒店、天气等查询。

长耗时规划不要阻塞普通 HTTP 请求直到完成；优先使用：

- SSE 返回生成进度。
- 异步任务 ID + 查询接口。
- WebSocket 仅在需要双向实时交互时使用。

## 4. 当前 API 契约 MVP 实现边界

当前源码已经按 `docs/api/API接口规范文档.md` 暴露 V1 主路径：

- `app/api/v1/auth.py`：手机号注册、短信验证码、手机号/密码登录、刷新 Token、登出；开发态短信验证码固定为 `123456`，JWT 由 `app/core/security.py` 生成。
- `app/api/v1/user.py`：用户资料、偏好配置、匿名会话合并；资料和偏好通过 `UserService`。
- `app/api/v1/chat.py`：会话创建/列表/删除、消息发送、SSE 流、消息历史；消息发送已接入 Agent SSE 编排，测试中使用本地 stub 验证契约形态。
- `app/api/v1/plan.py`：方案列表/详情/删除通过 `TravelPlanService`，生成/修改/重新生成返回 SSE stub，导出/分享/收藏为契约占位。
- `app/api/v1/data.py`：城市、景点、餐厅、酒店、天气；优先复用现有 data service，天气不调用外部服务。
- `app/api/v1/ops.py`：`/api/v1/health` 和 `/api/v1/tasks/{taskId}`。

旧路径 `/api/v1/conversations`、`/api/v1/travel-plans`、`/api/v1/users/me` 和根路径 `/health` 已移除，不再作为兼容入口。

统一响应由 `app/schemas/common.py` 提供：

- 成功响应：`BaseResponse`，字段为 `code/message/data/request_id`。
- 分页响应：`PaginatedData`，字段为 `list/total/page/page_size/total_pages`。
- 错误响应：`ErrorResponse`，业务错误码和 HTTP status 分离。

API 层允许做请求校验、响应封装和 SSE 事件组装；用户、对话和方案的业务数据边界仍落在 `services/application/`。真实短信、安全限流、导出渲染、SSE 断点续传、对话/方案完整持久化和部分天气/地图外部调用仍未完成，只保留契约形态或适配器边界。

## 5. RAG 与第三方数据当前边界

当前源码已经具备可执行的数据源适配和降级边界，但不等同于生产级数据闭环：

- `app/services/vector/`：Chroma 本地向量库封装，默认持久化目录为 `chroma_data/`，该目录是本地产物，不提交。
- 本地 Chroma 通过目录外侧的文件锁限制为单进程访问；后端在 lifespan 中获取锁、校验已有 collection，并在退出时显式关闭客户端。
- POI 灌数和全量重建使用影子目录，验证 PostgreSQL 行数、collection 数量和样例查询后原子切换；旧目录保留为时间戳备份。
- `app/services/vector/embedding.py`：通过 ModelScope 下载/缓存 `BAAI/bge-m3`，加载失败时使用 1024 维伪 embedding 降级，避免离线测试直接失败。
- `app/services/vector/rag.py`：统一执行 embedding → Chroma Top-K → reranker → final K 的召回链路，避免 Agent 和工具重复实现检索逻辑。
- `app/services/vector/reranker.py`：通过 ModelScope 下载/缓存 `BAAI/bge-reranker-base`，加载或推理失败时退回向量召回顺序。
- `app/agents/tools/tool_registry.py`：统一注册景点、餐厅、酒店、天气、路线、美团酒旅和 12306 查询工具；Agent 只能通过注册工具调用外部能力。
- `app/services/third_party/meituan.py`：通过本机 `mttravel` CLI 读取美团酒旅数据；服务启动时可将 `.env` 中的 `MEITUAN_TOKEN` 同步到 `~/.config/meituan-travel/config.json`，未安装 CLI 或未配置 Token 时必须返回可解释降级结果。
- `app/services/third_party/railway12306.py`：查询 12306 公开接口，作为出行建议数据源；不得把余票查询扩展为下单、支付或出票能力。

默认单元测试和契约测试不得依赖真实 Chroma 数据、BGE 模型缓存、mttravel CLI、12306 网络、地图/天气 Key 或真实 LLM Key。需要这些资源的测试必须标记 `integration`。
