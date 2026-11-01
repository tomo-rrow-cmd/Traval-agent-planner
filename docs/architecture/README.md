# AI旅行规划师技术架构设计

本目录集中维护 AI 旅行规划师项目的架构设计文档。原始技术架构设计文档已按一级章节拆分到 `chapters/`，多智能体协作旅行规划专题归档为 `multi-agent-collaboration.md`，数据库设计文档单独放在 `database/`，工程实现边界、后端实现快照和代码结构快照分别放在 `implementation/`、`backend/` 和 `snapshots/`。

实现时优先遵守 `implementation/` 中提炼的工程边界和 `.agent/decisions.md` 中的显式决策：V1.0 采用 `app/` 根目录下的模块化单体，复杂规划流程由 LangGraph 中央编排，真实预订、支付、订单履约等能力只做架构预留。客户端涵盖 Web（`frontend/` Vue 3）和 Android（`android/` Kotlin + Jetpack Compose）。

当前后端源码实现快照见 [`backend/`](backend/)。该目录用于快速理解现有模块、Agent 工具、RAG 和 API 状态；如果它与 `.agent/decisions.md` 冲突，以 `.agent/decisions.md` 为准。

## 目录结构

| 目录 | 内容 |
| --- | --- |
| `backend/` | 当前后端实现架构快照 |
| `chapters/` | 技术架构设计文档的拆分章节 |
| `database/` | 数据库表结构设计与说明 |
| `diagrams/` | PlantUML 图源文件与导出图片 |
| `implementation/` | 工程实现边界与协作口径 |
| `multi-agent-collaboration.md` | 多智能体协作旅行规划专题架构 |
| `snapshots/` | 当前代码结构快照 |

## 文档定位

| 文档 | 定位 | 使用方式 |
| --- | --- | --- |
| [软件架构设计文档](软件架构设计文档.md) | 软件架构主文档：分层架构、数据模型、Agent、编排管线、RAG、接口与部署 | 现行基线，其余架构文档与它口径冲突时以此为准 |
| [架构设计说明书](架构设计说明书.md) | 产品架构设计：产品定位、用户流程、功能分层、智能体协作模型 | 面向产品与验收视角，技术细节回溯主文档 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 后端实现架构速览：关键文件索引、实现状态、扩展指南 | 面向开发速查，不作为最终设计依据 |

建议阅读顺序：`架构设计说明书`（解决什么问题）→ `软件架构设计文档`（如何设计）→ `ARCHITECTURE.md`（代码在哪里）。

## 章节目录

> `chapters/` 目录下的章节为原始技术架构设计文档的拆分，属于历史设计稿。
> 各章节中的供应商名称、技术版本和接口描述以原始文档为准，不一定代表当前源码实现。
> 当前实际实现见 [`backend/`](backend/) 和后端架构文档 [`ARCHITECTURE.md`](ARCHITECTURE.md)；
> 协作边界与决策以 `.agent/decisions.md` 为准。

- [一、概述](chapters/01-概述.md)
- [二、整体技术架构](chapters/02-整体技术架构.md)
- [三、技术选型详解](chapters/03-技术选型详解.md)
- [四、多智能体架构设计](chapters/04-多智能体架构设计.md)
- [五、数据架构设计](chapters/05-数据架构设计.md)
- [六、API接口设计](chapters/06-API接口设计.md)
- [七、部署架构设计](chapters/07-部署架构设计.md)
- [八、安全架构设计](chapters/08-安全架构设计.md)
- [九、性能优化策略](chapters/09-性能优化策略.md)
- [十、可扩展性设计](chapters/10-可扩展性设计.md)
- [十一、开发规范与工程实践](chapters/11-开发规范与工程实践.md)
- [十二、V2.0架构演进规划](chapters/12-V2.0架构演进规划.md)

## 专题文档

- [架构决策详细正文 (docs/decisions/)](../decisions/)
- [架构设计说明书（产品架构）](架构设计说明书.md)
- [软件架构设计文档](软件架构设计文档.md)
- [配图源文件 (diagrams/)](diagrams/)
- [工程实现边界](implementation/README.md)
- [后端实现架构快照](backend/README.md)
- [当前代码结构快照](snapshots/code-structure.md)
- [数据库设计文档](database/数据库设计文档.md)
- [多智能体协作旅行规划架构](multi-agent-collaboration.md)
- [Android 客户端开发规范](../android/Android客户端开发规范.md)

## 维护说明

- 技术架构章节变更后，需要同步检查本 README 的章节目录。
- 数据库表结构、字段、索引和删除策略变更后，需要同步更新 `database/数据库设计文档.md`。
- 代码结构发生经确认的新增目录、迁移目录、模块重命名或入口调整后，需要同步更新 `snapshots/code-structure.md`。
- 当前天气、LLM、RAG 和第三方数据源口径以 `.agent/decisions.md` 的显式决策为准；历史章节中的供应商名称保留为原始架构方案，不一定代表当前源码默认实现。
