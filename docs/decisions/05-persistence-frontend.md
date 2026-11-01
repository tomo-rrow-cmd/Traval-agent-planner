# 持久化、API 与前端决策

> 索引：[.agent/decisions.md](../../.agent/decisions.md) · 范围：D-036 ~ D-044

## D-036：V1 导出任务采用进程内临时实现

- 决策：Markdown 同步导出，PDF、PNG、DOCX 使用进程内后台任务和临时文件，任务按用户隔离，产出保留 1 小时。
- 原因：尚未引入稳定任务队列和对象存储，先完整实现创建、查询、下载契约。
- 影响：任务不保证跨重启或多 worker 共享；生产化需迁移到持久化任务队列与对象存储。

## D-037：会话资源统一执行所有权校验

- 决策：会话、消息和方案运行记录的读写限定当前用户；不存在与越权访问统一返回 404。标题与置顶通过 PATCH 接口持久化。
- 原因：仅按 ID 查询会泄露其他用户数据，前端本地置顶无法跨设备一致。
- 影响：Repository 和 Service 查询必须携带 user_id；测试覆盖跨用户场景。

## D-038：会话消息与方案运行顺序通过行级锁和数据库唯一约束保证

- 决策：`sequence` 分配前先 `SELECT ... FOR UPDATE` 锁住 `conversations` 行；辅以三个数据库唯一约束兜底。消息幂等通过 `client_message_id` 唯一约束实现。
- 原因：ORM 层 `max(sequence) + 1` 在高并发下存在竞态；消息幂等是 SSE 重连和弱网场景的刚性需求。
- 影响：`add_message()` 和 `create_plan_run()` 必须在 `lock_conversation()` 后分配 sequence。

## D-039：消息历史同时支持页码和双向游标分页

- 决策：`GET /chat/sessions/{sid}/messages` 同时支持 `page/page_size` 和 `before_id/after_id` 两种分页，参数互斥。
- 原因：页码适合首次加载，游标适合"加载更多"并避免插入导致的重复/遗漏。
- 影响：Repository 提供两种查询；Service 层校验参数互斥；前端按场景选择。

## D-040：plan_result 消息的 metadata_json 只存 plan_run_id，summary 由 API 动态注入

- 决策：写入 `plan_result` 时只存 `{"plan_run_id": "..."}`；历史 API 通过 `_hydrate_messages()` 批量查询并注入 `metadata.summary`。
- 原因：summary 是大型 JSON，同时写入两处会导致数据重复和存储膨胀。
- 影响：`persist_plan_result()` 写消息不含 summary；`get_messages()` 响应阶段批量补全。前端从 `metadata.summary` 读取。

## D-041：前端 SSE 解析器必须处理流结束边界

- 决策：`chatStore` 的 SSE ReadableStream 循环在流结束后必须调用 `TextDecoder.decode()` 清空内部缓冲，并消费 `buffer` 中残留的事件行（含无尾随空行的事件）。
- 原因：`decoder.decode(value, { stream: true })` 会在 UTF-8 多字节序列跨 chunk 时保留内部状态；流结束时不 flush 会导致最后一条 SSE 事件丢失。
- 影响：SSE 解析器保持 `flushLines` 模式：循环内按行消费，循环结束后 flush decoder 并处理 buffer 残留；for 循环结束后 fallback 消费未触发空行分隔的 `event/data` 对。

## D-042：匿名会话 user_id 通过哈希适配 DB VARCHAR(36)

- 决策：`get_current_user` 对匿名会话的 `user_id` 使用 `anon:{md5(session_id)[:31]}` 生成固定 36 字符标识。
- 原因：`conversations.user_id` 定义为 `VARCHAR(36)`（为 UUID 设计），匿名 session_id 可能超长导致 `StringDataRightTruncationError`。
- 影响：匿名 `user_id` 不再包含原始 session_id，但同 session_id 在单次浏览器会话内稳定映射。

## D-043：前端启动脚本统一维护

- 决策：新增 `scripts/start_frontend.sh` 作为前端 Vite 开发服务器启动入口，自动检查 Node.js 18+、安装依赖，支持 `--port` 和 `--no-open`。
- 原因：保持前后端启动方式一致，减少新成员环境诊断成本。
- 影响：默认端口 5173 需与 `vite.config.ts` 保持一致；修改参数时同步更新 README。

## D-044：新增 Android 客户端平台

- 决策：在 Web 客户端之外新增 Android 客户端（Kotlin + Jetpack Compose），采用 MVVM + Repository 分层架构，复用后端 REST/SSE API。
- 原因：移动端是旅行场景的天然载体（行程执行、签到打卡、实时提醒）；Android 先行，iOS 后续评估。
- 影响：Android 代码位于 `android/` 顶层目录；开发规范见 `docs/android/Android客户端开发规范.md`；前后端契约（API/SSE）需保持 Android/Web 双端兼容；CI 现阶段不涵盖 Android 构建。
