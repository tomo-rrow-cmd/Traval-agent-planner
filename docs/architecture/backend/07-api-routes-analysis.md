# `app/api/v1/` 路由层逐行解析

> 对应源码目录: [app/api/v1/](../../../app/api/v1/)
> 路由注册入口: [app/api/router.py](../../../app/api/router.py)

---

## 1. 路由注册架构

在 [router.py](../../../app/api/router.py) 中，所有 v1 路由被统一挂载到 FastAPI app 上：

```
最终 URL = prefix("/api/v1") + 各 router 的 prefix
```

| 文件 | Router prefix | 最终 URL 前缀 | 职责 |
|---|---|---|---|
| [auth.py](../../../app/api/v1/auth.py) | `/auth` | `/api/v1/auth` | JWT 鉴权 |
| [chat.py](../../../app/api/v1/chat.py) | `/chat` | `/api/v1/chat` | 对话 + SSE 五阶段流水线 |
| [data.py](../../../app/api/v1/data.py) | `/data` | `/api/v1/data` | 基础数据（景点/酒店/餐厅/天气） |
| [ops.py](../../../app/api/v1/ops.py) | (无) | `/api/v1/` | 健康检查 + 任务下载 |
| [plan.py](../../../app/api/v1/plan.py) | `/plans` | `/api/v1/plans` | 方案 CRUD + 导出/分享 |
| [travelogue.py](../../../app/api/v1/travelogue.py) | `/travelogues` | `/api/v1/travelogues` | 游记 + 社交素材 + 分享 |
| [trip.py](../../../app/api/v1/trip.py) | `/trips` | `/api/v1/trips` | 行程执行 / 签到 / 花费 / 调整 |
| [user.py](../../../app/api/v1/user.py) | `/user` | `/api/v1/user` | 用户资料 + 偏好 |

---

## 2. auth.py — 认证接口

### 导入依赖（L1-27）

| 导入 | 用途 |
|---|---|
| `APIRouter, Depends` | FastAPI 路由分组 + 依赖注入 |
| `async_session_factory` | 异步 SQLAlchemy session 工厂，每次 `async with ... as db:` 创建新会话 |
| `User` | SQLAlchemy ORM 模型，映射到 `users` 表 |
| `create_access_token` | 签发 JWT access token（短有效期，如 2h），参数: `(user_id, extra_claims)` |
| `create_refresh_token` | 签发 JWT refresh token（长有效期） |
| `decode_refresh_token` | 解码验证 refresh token，返回 payload 或抛异常 |
| `hash_password` | 明文密码 bcrypt/argon2 哈希 |
| `verify_password` | 验证明文与哈希是否匹配 |
| `get_current_user` | FastAPI 依赖函数：从 `Authorization: Bearer <token>` 提取验证 JWT，返回 `{"user_id": ..., "phone": ...}` |
| `BaseResponse[T]` | 统一响应封装 `{code, message, data}` |
| `EmptyData` | 空对象 `{}` |
| `select` | SQLAlchemy 2.0 风格查询构造器 |

Router 实例化:
```python
router = APIRouter(prefix="/auth", tags=["认证接口"])
```

### 端点

#### `POST /auth/register` — 手机号+密码注册（L30-62）

```python
@router.post("/register", response_model=BaseResponse[TokenResult])
async def register(request: RegisterRequest):
```

逐行逻辑:
1. `async with async_session_factory() as db:` — 创建异步数据库会话
2. `select(User).where(User.phone == request.phone)` — 构造 `SELECT * FROM users WHERE phone = ?`
3. `db.execute(...)` — 异步执行；`.scalar_one_or_none()` — 提取单行或 `None`
4. `if existing: return BaseResponse(code=10002, message="手机号已注册")` — 业务错误不用 HTTP 异常，统一 HTTP 200 + 业务错误码
5. `User(phone=..., hashed_password=hash_password(request.password), nickname=request.nickname or f"旅行者{request.phone[-4:]}")` — 密码先哈希再存，昵称为空时自动生成
6. `db.add(user)` + `await db.commit()` — 持久化到数据库，commit 后 `user.id` 可用
7. `create_access_token(user.id, {"phone": user.phone})` + `create_refresh_token(user.id)` — 注册即登录
8. 返回 `TokenResult` 含 access_token、refresh_token、expires_in=7200、脱敏 UserProfile（手机号 `138****1234` 格式）

#### `POST /auth/sms-codes` — 发送短信验证码（L65-69）

```python
_ = request
return BaseResponse(data=SmsCodeResult())
```

Mock 实现：不管什么手机号始终返回成功，开发环境固定验证码 `123456`。

#### `POST /auth/sessions` — 登录（L72-115）

支持两种方式：

**验证码登录 (`method == "phone"`)**：
- 验证码固定 `"123456"`（开发环境）
- 用户不存在时**自动注册**（隐式注册），实现"输入验证码即注册+登录"

**密码登录 (`method == "password"`)**：
- 用户必须已注册
- `verify_password(request.password or "", user.hashed_password)` 验证密码哈希

**异常路径**：
- 不支持的方法 → `BaseResponse(code=10001, message="不支持登录方式")`

登录成功后签发双 token + 返回脱敏 UserProfile。

#### `POST /auth/tokens` — 刷新 Token（L118-143）

1. `decode_refresh_token(request.refresh_token)` — 解码验证，过期/无效/篡改抛异常
2. `payload["sub"]` — JWT 标准 claim `sub` = user_id
3. 从数据库反查用户是否存在（防止 token 有效但用户已被删除）
4. **Refresh Token Rotation**: 每次刷新同时下发新的 refresh token（旧 token 不主动失效，无状态 JWT 的取舍）
5. 返回新的双 token

#### `DELETE /auth/sessions/current` — 登出（L146-150）

```python
async def logout(current_user: dict = Depends(get_current_user)):
    _ = current_user
    return BaseResponse(data=EmptyData())
```

无状态登出：服务端不记录 session，仅验证 token 有效性，客户端删除本地 token 即可。

---

## 3. chat.py — 对话 + SSE 五阶段流水线

这是最复杂的路由文件，核心实现了文档 §4 五阶段流水线的 SSE 流式传输。

### 导入与常量（L1-40）

| 导入 | 用途 |
|---|---|
| `asyncio` | 异步队列 `asyncio.Queue`、`create_task`、`wait_for` |
| `contextlib` | `suppress()` 静默忽略指定异常 |
| `logging` | 结构化日志 |
| `StreamingResponse` | FastAPI SSE 响应类型 |
| `ConversationService` | 会话服务层，封装 CRUD、消息记录、方案持久化 |

常量:
```python
_SSE_DONE = object()           # 哨兵对象，标记事件流结束（用 object() 而非 None 避免歧义）
_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",  # 禁止缓存和代理转换
    "Connection": "keep-alive",                  # 长连接
    "X-Accel-Buffering": "no",                  # 禁用 nginx 缓冲
}
```

### 核心函数

#### `_format_sse_frame(event_id, event, data)` — SSE 帧格式化（L42-47）

按 SSE 协议输出:
```
id: evt_{n}\n
event: {type}\n
data: {json}\n\n
```

- `id:` — 事件序号，用于断点重连的 `Last-Event-ID`
- `event:` — 事件类型名（`step_start`, `progress`, `message_delta`, `done` 等）
- `data:` — JSON 序列化数据，`ensure_ascii=False` 保证中文不转义
- `\n\n` — SSE 帧分隔符

#### `_enqueue_sse_events(events, queue)` — 事件入队（L50-61）

**生产者协程**:
- 支持两种事件源：`__aiter__` 异步生成器 / 普通列表
- 统一放入 `asyncio.Queue`
- 异常时放入 `("error", ...)`
- `finally` 块确保始终发送 `_SSE_DONE` 哨兵

#### `sse_response(events, keepalive, keepalive_interval)` — SSE StreamingResponse 工厂（L64-104）

内部 `stream()` 异步生成器:

1. `asyncio.Queue(maxsize=1)` — **背压控制**：最多积压 1 个事件，防止内存爆炸
2. `asyncio.create_task(_enqueue_sse_events(...))` — 后台任务异步生产事件
3. `asyncio.wait_for(queue.get(), timeout=keepalive_interval)` — 带超时的队列读取
4. 15 秒无事件 → 发送 SSE 注释行 `: keepalive\n\n`（浏览器不触发事件但保持连接）
5. 收到 `_SSE_DONE` → 退出循环
6. `finally` 块取消未完成的 producer，等待 `CancelledError`
7. 返回 `StreamingResponse(stream(), media_type="text/event-stream")`

#### `_run_pipeline_events(session_id, message, user_id, history, service)` — 五阶段流水线（L107-194）

**阶段 1: 对话提取**:
- 延迟导入 `DeepSeekLLM` + `UserInteractionAgent`（避免循环依赖）
- 从 service 加载会话 context
- `ui.stream_response(...)` 异步生成器逐 token 产出 `delta` 事件
- `message_delta` 事件发送给前端实现打字机效果，含 `sequence` 防乱序
- `message` 事件发送完整回复并持久化 AI 回复

**守卫条件**（L159-161）:
```python
if not (mode == "travel_planning" and ready and confirmed):
    yield ("done", {"status": "waiting_input", ...})
    return
```
只有当用户意图是旅行规划、参数齐全、用户已确认时，才进入阶段 2-5。

**阶段 2-5: Pipeline 执行**:
- `run_pipeline(pipeline_params)` 返回 SSE 事件流
- 透传所有 pipeline 事件给前端
- `done` 事件到达时调用 `service.persist_plan_result()` 持久化方案
- 持久化失败时单独报错（方案已生成但保存失败）

#### `_agent_sse_events()` — 事件源封装（L197-206）

薄封装层，为测试留出 monkeypatch 接入点。

#### `_load_history()` — 加载历史消息（L209-212）

从 service 拉最近 50 条消息，提取 `role` + `content` 构建 LLM 所需的历史数组。兼容分页对象和普通列表两种返回类型。

### 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/chat/sessions` | 创建会话 |
| `GET` | `/chat/sessions` | 会话列表（分页） |
| `DELETE` | `/chat/sessions/{session_id}` | 删除会话 |
| `PATCH` | `/chat/sessions/{session_id}` | 更新会话 |
| `POST` | `/chat/sessions/{session_id}/messages` | **核心入口**：保存用户消息并返回 Agent SSE 流 |
| `GET` | `/chat/sessions/{session_id}/stream` | SSE 恢复（断线重连） |
| `GET` | `/chat/sessions/{session_id}/messages` | 消息列表（支持传统分页和游标分页，互斥） |
| `GET` | `/chat/sessions/{session_id}/plans` | 会话方案运行记录 |

#### `POST /chat/sessions/{session_id}/messages` 详情（L258-281）

1. `service.record_message(...)` — 持久化用户消息，返回 `(msg, created)`
2. **幂等性保护**：如果 `client_message_id` 已存在 → `created == False` → 返回 `idempotent_replay`，不重复执行 pipeline
3. `_load_history(...)` → 加载历史
4. `sse_response(_agent_sse_events(...))` → 启动 Agent SSE 流

#### `GET /chat/sessions/{session_id}/messages` 分页策略（L313-332）

- 传统分页: `page` + `page_size`
- 游标分页: `before_id` / `after_id` + `limit`
- 二者互斥，`BadRequestException` 校验

---

## 4. data.py — 基础数据接口

### 辅助函数

#### `_parse_price_range(price_range)` — 价格范围解析（L21-28）

取价格区间上限: `"200-500"` → `500.0`

#### ORM → Schema 转换函数（L30-79）

| 函数 | 输入 | 输出 | 特殊处理 |
|---|---|---|---|
| `_attraction_to_data` | `Attraction` ORM | `AttractionData` | `ticket_price`: `None`→"免费"；`suggest_duration`: 小时→分钟×60；`tags`: `None`→`[]` |
| `_restaurant_to_data` | `Restaurant` ORM | `RestaurantData` | `tags`: `None`→`[]` |
| `_hotel_to_data` | `Hotel` ORM | `HotelData` | `facilities`: `None`→`[]`；`tags` 固定 `[]` |

### 端点

| 方法 | 路径 | 说明 | 实现状态 |
|---|---|---|---|
| `GET` | `/data/cities` | 城市列表（`popular`/`keyword` 过滤） | 硬编码示例 |
| `GET` | `/data/attractions` | 景点列表（`city`/`tags` 过滤，分页） | 真实 DB 查询 |
| `GET` | `/data/attractions/{item_id}` | 景点详情 | 真实 DB 查询 |
| `GET` | `/data/restaurants` | 餐厅列表（`city`/`cuisine` 过滤，分页） | 真实 DB 查询 |
| `GET` | `/data/hotels` | 酒店列表（`city`/`price_range` 过滤，分页） | 真实 DB 查询 |
| `GET` | `/data/weather` | 天气查询（`city`/`date`） | **占位** |

各列表端点结构一致:
1. `Depends(get_db)` 注入 `AsyncSession`
2. 创建对应 Service
3. 调用 `service.search_by_*()` 查询
4. 手动映射 `_*_to_data()` 转换 schema
5. `PaginatedData.create(data, total=len(data), ...)` 构造分页对象

---

## 5. ops.py — 运维与任务接口

### 端点

#### `GET /health` — 健康检查（L12-26）

```python
return BaseResponse(data=HealthData(
    status="healthy", version="1.0.0", uptime_seconds=0,
    dependencies={
        "postgresql": "not_checked",
        "redis": "not_checked",
        "llm_service": "not_checked",
    },
))
```

所有依赖项标记 `not_checked`，`uptime_seconds=0` 均为占位值。

#### `GET /tasks/{task_id}` — 任务状态（L29-37）

延迟导入 `export_task_manager`（全局单例），查询异步导出任务状态。

#### `GET /tasks/{task_id}/download` — 任务下载（L40-56）

1. `export_task_manager.download(task_id, user_id)` — 获取任务（含权限校验）
2. 扩展名特殊处理：`format == "image"` → `png`
3. `Response(content=task.file_path.read_bytes(), media_type=task.mime_type, headers={"Content-Disposition": f'attachment; filename="..."'})` — 触发浏览器下载

---

## 6. plan.py — 方案接口

### SSE 占位函数

#### `plan_generation_events(plan_id)` — 方案生成 SSE 占位（L26-43）

返回预制的 SSE 事件序列：
- `message`（plan_progress）→ `step_start`（parallel_planning）→ `progress`(40%) → `progress`(85%) → `step_end` → `done`(含 plan_id + redirect_url)

契约 MVP 不真正运行 pipeline，前端借此开发 SSE 进度条 UI。

#### `plan_confirmation_required_events()` — 未确认提示（L46-59）

返回提示消息 + `done(status="waiting_confirmation")`，前端据此展示"确认/修改"按钮。

### 端点

| 方法 | 路径 | 说明 | 实现状态 |
|---|---|---|---|
| `GET` | `/plans` | 列表（分页 + `status` 过滤） | 真实 service |
| `POST` | `/plans` | 创建方案（SSE 流） | **SSE 占位** |
| `GET` | `/plans/{plan_id}` | 详情 | 真实 service |
| `PATCH` | `/plans/{plan_id}` | 局部修改（SSE 流） | **SSE 占位** |
| `POST` | `/plans/{plan_id}/generations` | 重新生成（SSE 流） | **SSE 占位** |
| `DELETE` | `/plans/{plan_id}` | 删除 | 真实 service |
| `POST` | `/plans/{plan_id}/exports` | 导出（md 同步；pdf/docx/png 异步） | 真实 |
| `POST` | `/plans/{plan_id}/shares` | 分享 | 真实 service |
| `POST` | `/plans/{plan_id}/favorites` | 收藏/取消收藏 | 真实 service |

#### `POST /plans` 两段式确认（L81-90）

```
请求 confirmed=false → SSE: "请先确认"
请求 confirmed=true  → SSE: plan_generation_events()
```

#### `POST /plans/{plan_id}/exports` 导出策略（L153-179）

1. 白名单校验格式: `("md", "docx", "pdf", "image")`
2. `model_dump()` 序列化方案数据
3. **Markdown**: 同步返回 `Response(content=..., media_type=...)` 下载
4. **PDF/DOCX/PNG**: 创建异步任务 → `schedule_export_task()` 后台执行 → 返回 `task_id` 供前端轮询

---

## 7. travelogue.py — 游记 & 社交素材

### 端点总览

#### 游记 CRUD

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/travelogues` | **AI 生成游记**（签到数据 + LLM） |
| `GET` | `/travelogues` | 列表（按 `status` 过滤） |
| `GET` | `/travelogues/{travelogue_id}` | 详情 |
| `PATCH` | `/travelogues/{travelogue_id}` | 编辑（title/content/cover_url/status） |
| `POST` | `/travelogues/{travelogue_id}/publish` | 发布（→ published） |

发布是独立端点而非 PATCH 的一部分，体现"编辑草稿"和"正式发布"是两个业务动作。

#### 社交素材

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/travelogues/materials/generate` | **一键生成社交素材**（9宫格/卡片/合集） |
| `GET` | `/travelogues/materials` | 素材列表（按 `trip_id`/`type` 过滤） |
| `POST` | `/travelogues/materials/{material_id}/favorite` | 收藏/取消收藏 |

#### 分享

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/travelogues/shares` | 生成分享链接 |
| `GET` | `/travelogues/shares/{share_code}` | 通过短码获取分享内容（无需登录） |

### 关键实现

#### `POST /travelogues` — AI 生成游记（L24-59）

1. `trip_service.list_checkins(trip_id, page_size=100)` — 拉签到记录
2. `trip_service.get_trip(trip_id)` — 拉行程信息
3. `TravelogueAgent(DeepSeekLLM()).generate({checkins, style, trip_info})` — LLM 生成标题、正文、封面、照片集、统计
4. `travelogue_service.create(...)` — 持久化

#### `POST /travelogues/materials/generate` — 社交素材（L117-153）

1. 同样拉取签到 + 行程信息
2. `agent.generate_social_materials(...)` — 批量生成 poster / card / collection / nine_grid
3. 循环 `travelogue_service.create_material(...)` 批量持久化，含 `layout` / `overlay_data` / `hashtags` 等社交媒体特有字段

#### `POST /travelogues/shares` — 分享链接（L184-204）

- `secrets.choice(...)` — 加密安全随机生成 8 位短码（优于 `random.choice`）
- `expire_at = datetime.utcnow() + timedelta(hours=request.expire_hours)` — 可选过期

#### `GET /travelogues/shares/{share_code}` — 公开访问（L207-216）

- 无需 `Depends(get_current_user)`，通过短码公开访问
- `service.increment_view(share_code)` — 每次访问递增 view 计数

---

## 8. trip.py — 行程执行

### 端点总览

#### Trip CRUD

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/trips` | **从方案创建行程实例** — "开始旅行" |
| `GET` | `/trips` | 列表（按 `status` 过滤） |
| `GET` | `/trips/{trip_id}` | 详情 |
| `PATCH` | `/trips/{trip_id}` | 更新状态: `active` / `paused` / `completed` / `abandoned` |
| `GET` | `/trips/{trip_id}/progress` | 实时进度（完成天数/签到数/花费统计） |

#### 签到

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/trips/{trip_id}/checkins` | 签到（含位置/时间/花费/照片/评分/备注） |
| `GET` | `/trips/{trip_id}/checkins` | 签到列表（按 `day` 过滤） |

#### 花费

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/trips/{trip_id}/expenses` | 记录花费（可关联 `checkin_id`） |
| `GET` | `/trips/{trip_id}/expenses` | 花费明细（按 `category` 过滤） |

#### 调整

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/trips/{trip_id}/adjustments/detect` | **AI 异常检测 + 生成调整** |
| `GET` | `/trips/{trip_id}/adjustments` | 调整历史（按 `status` 过滤） |
| `POST` | `/trips/{trip_id}/adjustments/{adj_id}/accept` | 接受调整 |
| `POST` | `/trips/{trip_id}/adjustments/{adj_id}/reject` | 拒绝调整 |
| `POST` | `/trips/{trip_id}/adjustments/{adj_id}/apply` | **应用调整**（执行到行程中） |

调整生命周期: `detect → pending → accept → apply`（或 reject）

#### 其他

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/trips/{trip_id}/reminder` | 次日提醒（AI 生成） |
| `POST` | `/trips/{trip_id}/photos/annotate` | AI 照片标注 |

### 关键实现

#### `POST /trips` — 开始旅行（L23-35）

从方案（Plan）创建行程执行实例（Trip），这是"计划→执行"的转换点。

#### `POST /trips/{trip_id}/checkins` — 签到（L86-103）

核心字段: `poi_type`, `poi_name`, `lat`/`lng`（位置）, `planned_at`/`actual_at`（计划 vs 实际时间）, `planned_cost`/`actual_cost`（计划 vs 实际花费）, `photos`, `rating`, `note`

#### `POST /trips/{trip_id}/adjustments/detect` — 异常检测（L150-179）

1. 延迟导入 `AdjustAgent` + `DeepSeekLLM`
2. 触发类型: `weather` / `late` / `closed` / `over_budget`
3. 输入当前日程 + 用户偏好 + 目的地
4. AI 生成 `original_plan` / `adjusted_plan` / `reason`
5. 持久化为调整建议（不自动应用，需用户确认）

#### `GET /trips/{trip_id}/reminder` — 次日提醒（L238-259）

`TripAgent.generate_reminder(...)` 生成天气、穿衣建议、出发时间、注意事项。`destination` 和 `day_outline` 当前传空（MVP 简化）。

---

## 9. user.py — 用户接口

### 端点

| 方法 | 路径 | 说明 | 实现状态 |
|---|---|---|---|
| `GET` | `/user/profile` | 获取用户资料 | 真实 service |
| `PUT` | `/user/profile` | 更新用户资料 | 真实 service |
| `GET` | `/user/preferences` | 获取偏好配置 | 真实 service |
| `PUT` | `/user/preferences` | 更新偏好配置 | 真实 service |
| `POST` | `/user/sessions/anonymous/merge` | 匿名数据合并 | **占位** |

### 关键细节

#### `PUT /user/preferences` — 全量替换（L56-68）

`preferences: UserPreferences` 参数在请求体中**直接作为 JSON body**（而非嵌套在 request 对象中），因为 schema 本身就是完整的偏好结构。

#### `POST /user/sessions/anonymous/merge` — 匿名合并（L71-78）

占位实现: `merged_plan_count=0`，匿名用户登录后将其浏览/创建的数据合并到登录账户（未实现真实逻辑）。

---

## 10. 全局模式总结

| 模式 | 说明 | 示例 |
|---|---|---|
| **统一响应** | 全部返回 `BaseResponse[T]`，HTTP 200 + 业务错误码，异常用全局 handler | `BaseResponse(code=10002, message="手机号已注册")` |
| **三层架构** | Router（校验/转发）→ Service（业务逻辑）→ Repository（数据库） | 所有端点均转发到对应 service |
| **依赖注入** | `Depends(get_current_user)` 鉴权、`Depends(get_*_service)` 注入服务 | `async def get_profile(current_user = Depends(get_current_user), user_service = Depends(get_user_service))` |
| **SSE 流** | `sse_response()` 工厂封装 `asyncio.Queue` + keepalive | chat.py, plan.py |
| **幂等性** | `client_message_id` 防重复提交 | chat.py L266-276 |
| **延迟导入** | Agent 和 LLM 在路由函数内部导入，避免循环依赖 | `from app.agents.travelogue_agent import TravelogueAgent` |
| **MVP 占位** | 城市/天气/方案生成/匿名合并等返回 mock 数据 | `BaseResponse(data=SmsCodeResult())` |
| **两段式确认** | SSE 流端点先检查 `request.confirmed`，未确认返回提示 | plan.py `create_plan`, `regenerate_plan` |
| **异步导出** | 同步返回 md，异步后台任务导出 pdf/docx/png | plan.py `POST /plans/{plan_id}/exports` |
| **调整生命周期** | detect → pending → accept → apply / reject | trip.py adjustments 端点 |
