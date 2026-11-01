# AI旅行规划师架构约束

本文件提炼 `docs/originals/AI旅行规划师技术架构设计文档.docx` 中对编码最重要的架构边界。实现时应优先遵守这些边界，避免把临时实现扩散为长期架构。

## 1. 产品阶段边界

### V1.0 范围

V1.0 聚焦“智能旅行规划方案自动生成”：

1. [架构文档总入口](../docs/architecture/README.md)
2. [架构决策索引](decisions.md) — 详细正文见 `docs/decisions/`
3. [AI 禁飞区](guardrails.md) — 禁止 AI 生成代码的模块与函数
4. [编码与协作规范](conventions.md) — 日常编码、接口、测试、提交和分支约束
5. [多智能体协作旅行规划架构](../docs/architecture/multi-agent-collaboration.md)
6. [工程实现边界](../docs/architecture/implementation/README.md)
7. [后端实现架构快照](../docs/architecture/backend/README.md)
8. [当前代码结构快照](../docs/architecture/snapshots/code-structure.md)
9. [数据库设计文档](../docs/architecture/database/数据库设计文档.md)
10. [API 接口规范文档](../docs/api/API接口规范文档.md)
11. [CI/CD 运行说明](../docs/CI-CD/ci-cd.md)
12. [Android 客户端开发规范](../docs/android/Android客户端开发规范.md)
13. [软件架构设计文档](../docs/architecture/软件架构设计文档.md)
14. [前端设计文档](../docs/front-docs/前端框架构建方案.md)
15. [需求设计说明书](../docs/requirements/需求设计说明书.md)
16. [AI 使用日志与反思报告](../docs/reports/ai-logs/)
17. [架构决策详细正文](../docs/decisions/)

### V2.0 范围

- `.agent/architecture.md` 保持为导航，不新增架构正文。
- 当前仓库事实基线是 `app/` 后端模块化单体、`frontend/` Vue Web 客户端与 `android/` Android 客户端组成的前后端单仓；数据库结构通过根目录 `alembic.ini` 和 `app/db/migrations/` 管理，当前迁移版本为 `20260717_02`。
- 后端启动入口包括：`main.py`（一键启动前后端，`python main.py`）、`scripts/start_backend.sh`（仅后端，Linux/macOS）、`scripts/start_backend.ps1` 和 `scripts/start_backend.cmd`（仅后端，Windows）；前端启动入口为 `scripts/start_frontend.sh`，默认端口 5173，API 代理到 localhost:8000。
- 当前完整规划必须经过用户显式确认，主图顺序为并行景点/美食/酒店 → 两轮决策与详情补全 → 交通 → 预算，超预算时经 adjust 回到并行阶段重跑（最多 2 次）；会话消息与每次方案版本分别持久化到 `messages` 和 `conversation_plan_runs`。景点规划已接入天气影响因子排序，交通 Agent 已支持去程/返程火车票分区查询。
- 除主编排 Agent 外，已实现独立调用 Agent：TripAgent（行程执行）、TravelogueAgent（游记生成）、PhotoPlannerAgent（上传照片 → Vision 提取偏好 → 生成方案）、WeatherAgent（天气查询与出行建议）、RouteOptimizerAgent（路线优化）、SouvenirAgent（纪念品推荐）。
- 会话方案的结构化事实唯一存放在 `conversation_plan_runs.summary`；`plan_result` 消息保存 Markdown 和 `plan_run_id`，历史 API 在响应阶段动态补充 summary。会话支持持久化标题更新和置顶排序。
- 消息持久化通过行级锁分配 sequence，辅以数据库唯一约束保证并发安全；消息幂等通过 `client_message_id` 唯一约束实现。消息历史同时支持页码和 `before_id`/`after_id` 双向游标分页。
- Markdown 导出同步返回；PDF、PNG、DOCX 通过 `app/services/export/` 使用单进程临时任务并通过任务状态和下载接口获取，任务不具备跨重启持久性。
- 修改目录结构、API 契约、外部服务默认供应商、CI 门禁、V1/V2 范围或新增客户端平台时，需要同步更新 `docs/architecture/` 下对应专题文档。
- 代码结构发生经确认的新增目录、迁移目录、模块重命名或入口调整后，需要同步更新 [当前代码结构快照](../docs/architecture/snapshots/code-structure.md)。
