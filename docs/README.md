# 项目文档目录

本目录集中存放 AI 旅行规划师项目的需求、架构、接口、计划和报告文档。面向开发协作的约束以仓库根目录 `.agent/` 为入口，正式需求、架构和接口说明以本目录文档为入口。

当前实现基线（2026-07-17）：仓库为 `app/` 后端、`frontend/` Web 客户端与 `android/` Android 客户端组成的前后端单仓，`main.py` 可一键启动前后端；完整方案经过用户确认后进入 LangGraph，两轮决策完成后写入 PostgreSQL 会话方案版本表。景点规划已接入天气影响因子排序，交通 Agent 已支持去程/返程火车票分区查询，已支持 Vision 图片识别（PhotoPlannerAgent 上传照片提取偏好），导出支持 Markdown 同步返回和 PDF/PNG/DOCX 异步任务。CI 已纳入前端 lint/typecheck/test/build 任务，覆盖率门禁为 84%。历史设计稿用于解释目标架构，理解当前代码时优先阅读后端实现快照、数据库设计和 `.agent/decisions.md`。

## 目录结构

| 目录 | 内容 |
| --- | --- |
| `android/` | Android 客户端开发规范 |
| `architecture/` | 技术架构设计文档、数据库设计、多智能体协作专题等架构类文档 |
| `api/` | API 接口规范与前后端协作契约 |
| `CI-CD/` | CI/CD 运行说明与流水线配置文档 |
| `decisions/` | 架构决策详细正文（按主题拆分） |
| `front-docs/` | 前端设计文档、视觉系统与开发报告 |
| `planning/` | 项目计划、优先级和里程碑相关文档 |
| `reports/` | 团队报告、每日提交总结、AI 使用日志与反思报告、测试报告等 |
| `reports/TBY-daily/` | 谭博友日报/周报 |
| `reports/CMJ-daily/` | 陈铭杰日报/周报 |
| `reports/FYW-daily/` | 封扬威日报/周报 |
| `reports/ai-logs/` | AI 使用日志与 Sprint 反思报告 |
| `reports/personal/` | 个人简历、求职文案与外部项目材料（仅本地保留，已加入 `.gitignore`，不入库） |
| `Sprint1/` | Sprint1 阶段验收、质量门禁、测试数据与报告 |
| `Sprint2/` | Sprint2 阶段验收、测试强化、代码走查与覆盖率报告 |
| `requirements/` | 需求设计文档 |
| `assets/` | 文档引用的图片等资源 |
| `originals/` | Word、Excel 等原始文件 |
| `need_fix/` | 已发现问题、修复方案、优化方案及测试报告 |

## 文档入口

- [技术架构拆分版](./architecture/README.md)
- [多智能体协作旅行规划架构](./architecture/multi-agent-collaboration.md)
- [工程实现边界](./architecture/implementation/README.md)
- [后端实现架构快照](./architecture/backend/README.md)
- [当前代码结构快照](./architecture/snapshots/code-structure.md)
- [数据库设计文档](./architecture/database/数据库设计文档.md)
- [API 接口规范文档](./api/API接口规范文档.md)
- [CI/CD 运行说明](./CI-CD/ci-cd.md)
- [架构决策详细正文](./decisions/)
- [Android 客户端开发规范](./android/Android客户端开发规范.md)
- [软件架构设计文档](./architecture/软件架构设计文档.md)
- [前端框架构建方案](./front-docs/前端框架构建方案.md)
- [前端界面设计文档](./front-docs/前端界面设计文档.md)
- [界面视觉设计系统](./front-docs/界面视觉设计系统.md)
- [需求设计说明书](./requirements/需求设计说明书.md)
- [后端修改方案](./need_fix/后端修改方案.md)
- [前端修改方案](./need_fix/前端修改方案.md)
- [项目优先级清单](./planning/项目优先级清单.md)
- [团队创建报告](./reports/团队创建报告.md)
- [AI 使用日志与反思报告](./reports/ai-logs/)
- [谭博友日报/周报](./reports/TBY-daily/)
- [陈铭杰日报/周报](./reports/CMJ-daily/)
- [封扬威日报/周报](./reports/FYW-daily/)
- [Sprint1 文档](./Sprint1/)
- [Sprint2 文档](./Sprint2/)

## 协作约定

- `.agent/architecture.md` 作为架构导航入口，指向 `docs/architecture/` 下的专题文档。
- `.agent/conventions.md` 记录编码、测试、分支和提交规范。
- `.agent/decisions.md` 记录已确认架构决策和待澄清问题。
- `.agent/guardrails.md` 划定 AI 禁飞区，列出禁止 AI 生成代码的模块与函数。
- `architecture/backend/` 记录当前后端实现快照，侧重源码模块、Agent/RAG/API 实现状态；正式协作边界仍以 `.agent` 和专题文档为准。

如果文档之间存在口径差异，优先查看 `.agent/decisions.md` 的显式决策，再回到对应专题文档补齐说明。调整目录结构或文档归档位置时，需要同步更新相关 README 和 `architecture/snapshots/code-structure.md`。
