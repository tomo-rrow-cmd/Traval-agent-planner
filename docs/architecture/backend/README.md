# 后端实现架构快照

本目录记录当前后端源码实现快照。正式协作边界以 `.agent/decisions.md` 的显式决策、`.agent/conventions.md` 的协作规范和 `docs/architecture/` 下的专题文档为准。

## 阅读顺序

1. [整体架构与数据库](01-overall-and-data.md)
2. [RAG 系统](02-rag.md)
3. [Agent 系统](03-agents.md)
4. [API 与第三方服务](04-api-and-integrations.md)
5. [关键文件索引与扩展指南](05-code-index-and-extension.md)
6. [后端代码说明文档（逐行讲解用）](06-backend-code-explanation.md)
7. [API 路由分析](07-api-routes-analysis.md)

## 维护说明

- 本目录用于快速理解当前源码模块、Agent 工具、RAG、API 和第三方适配状态。
- 代码结构发生经确认的新增目录、迁移目录、模块重命名或入口调整后，需要同步更新 [当前代码结构快照](../snapshots/code-structure.md)。
- API 契约变更优先更新 [API 接口规范文档](../../api/API接口规范文档.md)，再同步本目录中的实现快照。
- 如果本目录内容与 `.agent/decisions.md` 冲突，以 `.agent/decisions.md` 为准。
