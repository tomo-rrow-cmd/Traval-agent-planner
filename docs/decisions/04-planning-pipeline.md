# 规划管线与 SSE 决策

> 索引：[.agent/decisions.md](../../.agent/decisions.md) · 范围：D-027 ~ D-035

## D-027：后端本地启动通过跨平台脚本统一

- 决策：后端启动入口统一为 `scripts/start_backend.sh`（及 `.ps1`/`.cmd`）；脚本自动设置 `PYTHONPATH` 并按优先级选择 Python 运行器。
- 原因：统一启动器减少 `ModuleNotFoundError` 等环境诊断成本。
- 影响：默认只做依赖和连通性检查，不自动初始化数据库或重建向量库；`--init-db`、`--rebuild-vectors` 为显式参数。

## D-028：对话阶段采用增量 SSE 输出

- 决策：对话阶段先发送 `message_delta` 增量事件，再发送完整 `message`；SSE 响应禁用缓冲并支持 keepalive。
- 原因：用户需尽快看到 LLM 回复片段，反向代理和浏览器不可缓冲。
- 影响：前端按 `sequence` 组装增量，内部 READY 哨兵不得直接透出。

## D-029：LangGraph 规划进度以节点更新为准

- 决策：规划管线通过 `astream(stream_mode="updates")` 输出节点进度；`summary` 同时保留 `daily_itinerary` 和 `daily_plan`。
- 原因：固定模拟进度无法反映真实编排状态，新旧字段共存减少联调破坏。
- 影响：新增或重命名节点时需更新进度映射、测试和前端展示。

## D-030：推荐数据源增强但不进入交易闭环

- 决策：景点保留门票价格；酒店优先美团酒旅并标识真实价格，缺失时降级为 RAG/高德估算；交通查询公交/步行/驾车方案；12306 补充车站名、席别和实时票价。
- 原因：方案展示需更完整的价格和路线上下文，但当前仍以查询和推荐为主。
- 影响：字段必须允许缺失或估算，通过 `estimated`、`price_verified`、`source` 表达可信度；离线测试使用 mock/stub。

## D-031：方案生成必须经过显式确认

- 决策：所有触发生成的入口都必须在用户确认后才启动完整规划；未确认时只返回等待确认的 SSE 消息。
- 原因：完整规划触发 LangGraph、多 Agent、RAG 和第三方数据源，不应误触发高成本操作。
- 影响：前端需传 `confirmed: true`；测试覆盖未确认不规划、确认后进入规划、闲聊不触发规划三种路径。

## D-032：同一会话支持多次方案生成记录

- 决策：`conversation_plan_runs` 表保存每次方案生成的摘要和序号；`conversations.plan_id` 仅指向最新一次运行。
- 原因：用户常在同一对话中修改参数重新生成，单一 `plan_id` 会丢失历史上下文。
- 影响：`summary` 保存完整结构化结果；创建 run 与更新会话在同一事务提交。

## D-033：预算分层区分总额、应急预留和规划额度

- 决策：同时保留 `total_budget`、`reserve_budget`、`planning_budget`；超支判断优先使用 `planning_budget`。
- 原因：用户常说"总预算 N，留 M 应急"，直接按总预算安排会挤占预留资金。
- 影响：对话抽取、PlannerState、预算 Agent、前端请求和 `trip_config` 都需保留这组字段。

## D-034：当前主规划图采用确认门控和两轮决策

- 决策：完整规划仅在 `ready=true, confirmed=true` 后启动；主图固定为并行规划 → Decision R1 → Detail → Decision R2 → Traffic → Budget；预算重试时经 adjust 回到并行阶段。
- 原因：参数确认避免误触发外部调用；先定景点餐厅、再按通勤选酒店、最后完整交通，保证数据依赖顺序一致。
- 影响：WeatherAgent、RouteOptimizerAgent、SouvenirAgent 保留但非主图必经节点。

## D-035：对话方案结构化数据采用单一来源

- 决策：`conversation_plan_runs.summary` 是结构化数据唯一持久化来源；`plan_result` 消息保存 Markdown 和 `plan_run_id`，历史 API 读取时动态注入 summary。
- 原因：完整 summary 同时写入 run 和消息元数据会造成大型 JSON 重复和存储膨胀。
- 影响：创建 run、更新会话和写入结果消息在同一事务提交；旧 `__PLAN__:` 消息仅保留读取兼容。
