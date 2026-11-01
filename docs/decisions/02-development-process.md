# 开发流程与 CI 决策

> 索引：[.agent/decisions.md](../../.agent/decisions.md) · 范围：D-009 ~ D-020

## D-009：Git 分支采用 main + dev + feature/*

- 决策：本仓库使用 `main` 稳定分支、`dev` 开发分支、`feature/*` 功能分支；仅包含文档、注释、结构快照或协作规范的维护类改动，可在当前分支直接提交。
- 原因：用户明确指定轻量分支策略，同时确认文档相关改动不必新建分支。
- 影响：`docs/originals/` 中的 `develop/release/hotfix` Git Flow 说明不作为当前执行规范；如需发布分支需另行确认。

## D-010：Commit 类型收敛为 feat/fix/docs/refactor

- 决策：提交格式为 `<type>: <简述>`；有对应 Issue 时使用 `<type>: <简述> #<Issue编号>`。`type` 仅允许 `feat`、`fix`、`docs`、`refactor`。
- 原因：用户明确指定提交类型，并要求提交尽量关联 Issue。
- 影响：暂不使用 `chore`、`test`、`style`、`perf` 等类型；确需使用时先更新本决策。

## D-011：默认时区为 Asia/Shanghai

- 决策：系统内部和接口默认采用东八区 `Asia/Shanghai`，日期时间对外使用 ISO 8601。
- 原因：项目当前文档、用户环境和主要服务目标均以国内旅行为主。
- 影响：跨时区旅行、境外城市、多币种预算属于待确认扩展范围。

## D-012：保护当前代码结构

- 决策：当前仓库结构以 `docs/architecture/snapshots/code-structure.md` 为基准。不要轻易调整现有文件结构，如需修改请先和用户沟通。
- 原因：当前结构反映现阶段团队协作和模块划分；未经沟通的目录迁移会增加协作成本和合并风险。
- 影响：新增顶层目录、移动文件、重命名包、改变入口文件、调整模块归属边界前，必须先向用户说明方案并取得确认。

## D-013：数据库设计文档归档位置与优先级

- 决策：数据库设计文档放在 `docs/architecture/database/数据库设计文档.md`；架构拆分章节放在 `docs/architecture/chapters/`。
- 原因：数据库设计属于架构专题，独立目录能避免和按一级章节拆分的技术架构文档混放。
- 影响：数据库字段说明、索引、删除策略和数据类型以该数据库设计文档为准。

## D-014：API 契约以 `docs/api/API接口规范文档.md` 为准

- 决策：V1 公开 API 路径、统一响应、分页字段和 SSE 事件协议以 API 规范文档为准；源码移除旧路径。
- 原因：前后端协作需要稳定的单一 API 契约，避免 README、测试和源码各自维护不同路径。
- 影响：新增或修改接口时必须同步 API 文档、测试和代码结构快照。

## D-015：契约 MVP 不等同于真实能力完成

- 决策：当前认证、SSE、导出、任务状态和基础数据接口先实现契约 MVP，占位返回必须稳定、可测试。
- 原因：先让前后端按接口协议联调，同时不提前引入真实短信、导出渲染或外部服务依赖。
- 影响：开发态占位不能作为生产能力；接入真实实现时必须保持现有 wire shape 兼容。

## D-016：API 错误响应和测试基线纳入契约

- 决策：FastAPI/Starlette 的默认校验错误必须转换为统一错误响应；业务错误码与 HTTP status 分离。
- 原因：默认 422/404 响应结构会破坏前后端约定；纳入测试可以防止回退到框架默认格式。
- 影响：新增接口时必须补充测试，确认响应包含 `code/message/data/request_id`。

## D-017：CI/CD 使用 GitLab CI

- 决策：当前仓库使用 GitLab CI，流水线入口为 `.gitlab-ci.yml`；适配带 `shell` tag 的 GitLab shell runner。
- 原因：远端仓库位于 GitLab，runner 以本机 shell executor 为主。
- 影响：新增 CI 检查优先写入 `.gitlab-ci.yml`；真实 CD 落地前需确认 Runner 能力、Container Registry 和部署目标。

## D-018：Python 版本统一为 3.12

- 决策：本地开发、CI 和容器运行统一使用 Python 3.12。
- 原因：避免不同环境因依赖 wheel 或语法兼容性产生差异。
- 影响：`.gitlab-ci.yml` 和 `Dockerfile` 必须使用 Python 3.12 基础环境。

## D-019：默认 CI 只跑离线测试

- 决策：默认 CI pytest 命令为 `python -m pytest -m "not integration" tests --cov=app --cov-fail-under=84`；需要外部资源的测试标记为 `integration`。
- 原因：CI 门禁应稳定、可复现、低成本，不能因外部资源缺失阻塞普通提交。
- 影响：单元测试和契约测试必须通过 mock/stub/monkeypatch 隔离外部依赖；覆盖率不低于 84%。

## D-020：当前仓库基线为前后端单仓、后端模块化单体

- 决策：仓库同时维护 `app/` 后端模块化单体、`frontend/` Vue Web 客户端和 `android/` Android 客户端（Kotlin + Jetpack Compose）；后端不新增 `backend/` 包装目录。
- 原因：前端和 Android 客户端已进入仓库，后端以 `app/` 为稳定根目录。
- 影响：前后端契约变更需同步 API 文档和 Web/Android 双端类型；新增顶层目录或移动模块前必须确认。
