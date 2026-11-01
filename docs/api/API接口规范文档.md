# AI旅行规划师 — API 接口规范文档

> 定义前后端通信的接口协议、数据结构与交互模式，作为前端开发与后端开发的协作契约。
>
> **配套文档**：[项目文档入口](../README.md)、[后端实现架构快照](../architecture/backend/README.md)

---

## 目录

1. [通用约定](#一通用约定)
2. [认证接口](#二认证接口)
3. [用户接口](#三用户接口)
4. [对话接口](#四对话接口)
5. [方案接口](#五方案接口)
6. [基础数据接口](#六基础数据接口)
7. [运维与元信息接口](#七运维与元信息接口)
8. [扩展说明](#八扩展说明)

---

## 一、通用约定

### 1.1 基础信息

| 项目 | 值 |
|------|-----|
| 基础 URL | `/api/v1` |
| 数据格式 | JSON (UTF-8) |
| 时间格式 | ISO 8601 with timezone，如 `2026-07-06T14:30:00+08:00` |
| 时区 | `Asia/Shanghai` |
| 字符编码 | UTF-8 |

### 1.2 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req_20260706_abc123"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 0 表示成功，非 0 表示业务错误 |
| `message` | string | 成功为 `"ok"`，失败为错误描述（不暴露堆栈/密钥/SQL 等内部信息） |
| `data` | object/array | 响应数据，失败时为 `null` |
| `request_id` | string | 请求唯一标识，用于分布式追踪 |

### 1.3 翻页响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "request_id": "req_20260706_abc123"
}
```

翻页请求参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码，从 1 开始 |
| `page_size` | int | 20 | 每页条数，最大 100 |
| `sort_by` | string | — | 排序字段 |
| `sort_order` | string | `asc` | 排序方向，`asc` 或 `desc` |

### 1.4 游标翻页（消息历史专用）

对于有实时数据追加的场景（如消息历史），在 page/page_size 之外补充游标翻页：

| 参数 | 类型 | 说明 |
|------|------|------|
| `before_id` | string | 取此 ID 之前的数据（加载更早历史），与 `page` / `after_id` 互斥 |
| `after_id` | string | 取此 ID 之后的数据（加载新消息），与 `page` / `before_id` 互斥 |
| `limit` | int | 返回条数，默认 50，最大 100 |

游标翻页响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [],
    "has_more": true,
    "next_before_id": "msg_050",
    "next_after_id": null
  },
  "request_id": "req_20260706_abc123"
}
```

`before_id` 翻页时使用 `next_before_id` 续页，`after_id` 翻页时使用
`next_after_id` 续页。与查询方向无关的续页字段为 `null`。游标不存在或不属于
当前会话时返回 `400 / code=10001`。

### 1.5 SSE 事件协议

**Content-Type**: `text/event-stream`

**事件类型**：

| 事件 | 触发时机 | data 示例 |
|------|---------|-----------|
| `message_delta` | 对话回复增量片段 | `{"role": "assistant", "content_delta": "请问", "sequence": 1}` |
| `message` | 对话回复/追问 | `{"role": "assistant", "content": "请问从哪个城市出发？", "message_type": "question", "suggestions": ["北京", "上海", "广州"]}` |
| `step_start` | 规划阶段开始 | `{"step": "info_collection", "label": "正在了解您的需求..."}` |
| `progress` | 阶段内进度更新 | `{"percent": 45, "message": "景点筛选完成，正在规划交通路线"}` |
| `step_end` | 规划阶段结束 | `{"step": "parallel_planning"}` |
| `done` | 持久化成功后全流程完成 | `{"plan_run_id": "run_20260706_abc", "plan_id": "run_20260706_abc", "session_id": "sess_20260706_abc", "summary": {...}}` |
| `error` | 异常发生时 | `{"code": 50001, "message": "暂时无法完成规划，请稍后重试"}` |

**SSE 事件消息类型**（`message_type` 字段）：

| 类型 | 说明 | 附带字段 |
|------|------|---------|
| `text` | 普通文本回复 | — |
| `question` | AI 追问（需要用户输入） | `suggestions[]` — 快捷选项列表 |
| `plan_progress` | 规划进度 | — |
| `plan_result` | 方案结果（包含完整方案） | `plan_id` |

**SSE 重连规范**：

| 参数 | 值 | 说明 |
|------|------|------|
| **Last-Event-ID** | 约定 | 客户端记录最后接收的事件 ID，重连时通过 HTTP Header `Last-Event-ID` 带上；服务端从该 ID 之后重新推送，避免重复 |
| **心跳** | 每 30 秒 | 服务端每 30 秒发送一行 `: keepalive` 注释（SSE 规范的空事件），用于检测连接有效性 |
| **重连延迟** | 客户端控制 | 指数退避：1s → 2s → 4s → 8s → 16s → 30s（封顶），最多 10 次 |
| **恢复端点** | `GET /api/v1/chat/sessions/{sessionId}/stream` | 恢复已持久化的完成方案，暂不支持事件级断点续传 |

### 1.6 鉴权方式

| 认证方式 | 说明 |
|---------|------|
| **登录用户** | Header: `Authorization: Bearer <access_token>` |
| **匿名会话** | Header: `X-Session-Id: <session_id>` |
| **Token 有效期** | Access Token 2 小时，Refresh Token 7 天 |

Token 刷新：

```
POST /api/v1/auth/tokens
Body: { "refresh_token": "xxx" }
Response: { "access_token": "new_token", "refresh_token": "new_refresh", "expires_in": 7200 }
```

### 1.7 限流（Rate Limiting）

| 维度 | 阈值 | 响应头 | 说明 |
|------|------|--------|------|
| 全局限流 | 1000 QPS | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` | 超过返回 429 + 错误码 10004 |
| 用户级限流 | 100 QPS/用户 | 同上 | 按用户 ID 或 X-Session-Id 限流 |
| IP 级限流 | 200 QPS/IP | 同上 | 未登录请求按 IP 限流 |
| 短信接口 | 1 次/60 秒/手机号，5 次/天/手机号 | 同上 | 超出返回 20005 |

**429 响应示例**：

```json
{
  "code": 10004,
  "message": "请求频率过高，请 30 秒后重试",
  "data": null,
  "request_id": "req_20260706_abc123"
}
```

**响应头**：
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1720268400
Retry-After: 30
```

### 1.8 错误码体系

**通用错误码（10000-19999）**：

| 编码 | 说明 | 对应的 HTTP 状态码 |
|------|------|-------------------|
| 10000 | 成功 | 200 |
| 10001 | 请求参数错误 | 400 |
| 10002 | 缺少必填参数 | 400 |
| 10003 | 资源不存在 | 404 |
| 10004 | 请求频率过高 | 429 |

**认证错误码（20000-29999）**：

| 编码 | 说明 |
|------|------|
| 20001 | 未登录 |
| 20002 | Token 无效 |
| 20003 | Token 已过期 |
| 20004 | 无权限 |
| 20005 | 验证码错误/已过期 |
| 20006 | 验证码发送过于频繁（60 秒内仅可发一次） |
| 20007 | 当日验证码发送次数已达上限 |

**方案错误码（40000-49999）**：

| 编码 | 说明 |
|------|------|
| 40001 | 方案正在生成中 |
| 40002 | 方案生成中，请稍后 |
| 40003 | 方案生成失败 |
| 40004 | 无权修改此方案 |
| 40005 | 方案导出失败 |
| 40006 | 导出格式不支持 |

**对话错误码（50000-59999）**：

| 编码 | 说明 |
|------|------|
| 50001 | 会话不存在 |
| 50002 | 消息内容过长 |
| 50003 | 超出对话轮次限制 |

**第三方服务错误码（60000-69999）**：

| 编码 | 说明 |
|------|------|
| 60001 | 地图服务异常 |
| 60002 | 天气服务异常 |
| 60003 | AI 模型服务异常 |

**任务错误码（70000-79999）**：

| 编码 | 说明 |
|------|------|
| 70001 | 任务不存在 |
| 70002 | 任务尚未完成 |

### 1.9 通用数据校验规则

- 所有外部输入必须校验：类型、长度、格式、取值范围
- 字符串类型最大长度限制：标题 100 字符，描述 2000 字符，地址 255 字符
- 手机号格式：中国大陆 11 位数字
- 日期格式：`YYYY-MM-DD`
- 金额单位：人民币元（`DECIMAL(10,2)`）

---

## 二、认证接口

### 2.1 手机号密码注册

```
POST /api/v1/auth/register
```

**请求体**：

```json
{
  "phone": "13812345678",
  "password": "password123",
  "nickname": "旅行者"
}
```

**响应体 `data`**：

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "expires_in": 7200,
  "user": {
    "id": "user_xxx",
    "phone": "138****5678",
    "nickname": "旅行者"
  }
}
```

当前契约 MVP 会直接创建用户并签发 JWT；生产环境需要补齐密码强度策略、重复注册错误口径、短信/图形验证码和安全限流。

### 2.2 发送短信验证码

```
POST /api/v1/auth/sms-codes
```

**请求体**：

```json
{
  "phone": "13812345678"
}
```

**响应体 `data`**：

```json
{
  "expires_in": 60,
  "retry_after": 60
}
```

**安全约束**：

| 约束 | 值 | 超过后行为 |
|------|------|---------|
| 同一手机号发送间隔 | 60 秒 | 返回错误码 20006 |
| 同一手机号每日上限 | 5 次 | 返回错误码 20007 |
| 是否需要图形验证码 | 单 IP 当天发超过 10 次后需图形验证 | 在响应的 `data` 中返回 `need_captcha: true` |

### 2.3 手机号验证码/密码登录

```
POST /api/v1/auth/sessions
```

**请求体**：

```json
{
  "method": "phone",
  "phone": "13812345678",
  "code": "123456"
}
```

密码登录时 `method` 为 `password`，请求体使用 `password` 字段：

```json
{
  "method": "password",
  "phone": "13812345678",
  "password": "password123"
}
```

**响应体 `data`**：

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "expires_in": 7200,
  "user": {
    "id": "user_xxx",
    "phone": "138****5678",
    "nickname": "旅行者",
    "avatar_url": "https://..."
  }
}
```

### 2.4 刷新 Token

```
POST /api/v1/auth/tokens
```

**说明**：刷新 Token 与创建 Token 共用同一端点，通过 body 中携带 `refresh_token` 区分。

**请求体**：

```json
{
  "refresh_token": "eyJhbGciOi..."
}
```

**响应体 `data`**：

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "expires_in": 7200
}
```

### 2.5 登出

```
DELETE /api/v1/auth/sessions/current
```

**响应体 `data`**：`{}`

### 2.6 接口汇总

| 方法 | 路径 | 说明 | 鉴权 | 请求体 | 响应体 data |
|------|------|------|------|--------|-------------|
| POST | `/auth/register` | 手机号密码注册 | 否 | `{ phone, password, nickname? }` | `{ access_token, refresh_token, expires_in, user }` |
| POST | `/auth/sms-codes` | 发送短信验证码 | 否 | `{ phone }` | `{ expires_in, retry_after }` |
| POST | `/auth/sessions` | 手机验证码/密码登录 | 否 | `{ method, phone, code? password? }` | `{ access_token, refresh_token, expires_in, user }` |
| POST | `/auth/tokens` | 刷新 Token | 否 | `{ refresh_token }` | `{ access_token, refresh_token, expires_in }` |
| DELETE | `/auth/sessions/current` | 登出 | 是 | — | `{}` |

---

## 三、用户接口

### 3.1 获取用户资料

```
GET /api/v1/user/profile
```

**响应体 `data`**：

```json
{
  "id": "user_xxx",
  "phone": "138****5678",
  "nickname": "旅行者",
  "avatar_url": "https://...",
  "created_at": "2026-06-01T10:00:00+08:00"
}
```

### 3.2 更新用户资料

```
PUT /api/v1/user/profile
```

**请求体**：

```json
{
  "nickname": "新昵称",
  "avatar_url": "https://..."
}
```

**响应体 `data`**：更新后的 `UserProfile`

### 3.3 获取偏好配置

```
GET /api/v1/user/preferences
```

**响应体 `data`**：

```json
{
  "travel_style": "relaxed",
  "budget_level": "cost_effective",
  "pace": "moderate",
  "diet_preferences": ["chinese", "local_snacks"],
  "food_taboos": ["spicy"],
  "accommodation": "business",
  "transport": "time_first",
  "start_time": "09:00",
  "end_time": "21:00",
  "need_nap": false,
  "avoid_tags": ["commercial", "long_queue"],
  "must_visit_places": [],
  "special_requests": "",
  "custom_agent_name": "小旅",
  "agent_personality": "friendly"
}
```

#### UserPreferences 字段说明

| 字段 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| `travel_style` | string | `relaxed` / `balanced` / `intensive` / `food` / `culture` / `adventure` | 旅行风格 |
| `budget_level` | string | `budget` / `cost_effective` / `quality` / `luxury` | 预算等级 |
| `pace` | string | `easy` / `moderate` / `packed` | 行程节奏 |
| `diet_preferences` | string[] | 如 `["chinese", "local_snacks", "japanese"]` | 饮食偏好（多选） |
| `food_taboos` | string[] | 如 `["spicy", "seafood"]` | 食物禁忌 |
| `accommodation` | string | `hostel` / `business` / `boutique` / `luxury` | 住宿偏好 |
| `transport` | string | `time_first` / `cost_first` / `comfort` / `public` / `self_drive` | 交通偏好 |
| `start_time` | string | `"08:00"` / `"09:00"` / `"10:00"` | 每日开始时间 |
| `end_time` | string | `"20:00"` / `"21:00"` / `"22:00"` / `"24:00"` | 每日结束时间 |
| `need_nap` | boolean | `true` / `false` | 是否需要午休 |
| `avoid_tags` | string[] | 如 `["commercial", "long_queue", "tourist_trap"]` | 避坑标签 |
| `must_visit_places` | string[] | 如 `["故宫", "长城"]` | 必去地点 |
| `special_requests` | string | 自由文本 | 特殊要求 |
| `custom_agent_name` | string | 如 `"小旅"` | AI 助手名称 |
| `agent_personality` | string | `friendly` / `professional` / `humorous` / `lively` | AI 性格 |

### 3.4 更新偏好配置

```
PUT /api/v1/user/preferences
```

**请求体**：同上 `UserPreferences` 结构（允许部分更新）

**响应体 `data`**：更新后的完整 `UserPreferences`

### 3.5 匿名数据合并（登录后调用）

```
POST /api/v1/user/sessions/anonymous/merge
```

**请求体**：

```json
{
  "anonymous_session_id": "sess_anonymous_abc123"
}
```

**响应体 `data`**：

```json
{
  "merged_plan_count": 3
}
```

将匿名会话下生成的方案合并到当前登录用户账号下。

### 3.6 接口汇总

| 方法 | 路径 | 说明 | 鉴权 | 请求体 | 响应体 data |
|------|------|------|------|--------|-------------|
| GET | `/user/profile` | 获取用户资料 | 是 | — | `UserProfile` |
| PUT | `/user/profile` | 更新用户资料 | 是 | `UserProfile` 子集 | `UserProfile` |
| GET | `/user/preferences` | 获取偏好配置 | 是 | — | `UserPreferences` |
| PUT | `/user/preferences` | 更新偏好配置 | 是 | `UserPreferences` 子集 | `UserPreferences` |
| POST | `/user/sessions/anonymous/merge` | 合并匿名数据 | 是 | `{ anonymous_session_id }` | `{ merged_plan_count }` |

---

## 四、对话接口

### 4.1 创建新会话

```
POST /api/v1/chat/sessions
```

**请求体**：

```json
{
  "title": "大理3日游规划"
}
```

**响应体 `data`**：

```json
{
  "id": "sess_20260706_abc",
  "title": "大理3日游规划",
  "status": "active",
  "message_count": 0,
  "pinned": false,
  "created_at": "2026-07-06T14:30:00+08:00",
  "updated_at": "2026-07-06T14:30:00+08:00"
}
```

### 4.2 获取会话列表

```
GET /api/v1/chat/sessions?page=1&page_size=20
```

**响应体 `data`**：

```json
{
  "list": [
    {
      "id": "sess_20260706_abc",
      "title": "大理3日游规划",
      "status": "active",
      "message_count": 12,
      "pinned": true,
      "last_message_preview": "好的，这是为您生成的行程方案...",
      "created_at": "2026-07-06T14:30:00+08:00",
      "updated_at": "2026-07-06T15:00:00+08:00"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 4.3 更新会话

```
PATCH /api/v1/chat/sessions/{sessionId}
```

请求体至少包含一个字段：`title`（去除首尾空格后 1～100 字符）或 `pinned`（boolean）。
响应体 `data` 为更新后的完整会话对象。会话列表按 `pinned` 降序、`updated_at` 降序排列。

### 4.4 删除会话

```
DELETE /api/v1/chat/sessions/{sessionId}
```

**响应体 `data`**：`{}`

### 4.5 发送消息

```
POST /api/v1/chat/sessions/{sessionId}/messages
```

**请求体**：

```json
{
  "content": "我想去大理玩3天",
  "client_message_id": "client_0198f2f0"
}
```

`client_message_id` 由客户端首次发送时生成，网络重试必须复用同一值。同一会话中重复
提交不会再写入用户消息或重复启动规划。

**响应**：**SSE 流**（Content-Type: `text/event-stream`）

SSE 事件序列示例：

```
event: message
data: {"role": "assistant", "content": "好的！我来帮您规划大理3日游。请问您从哪个城市出发？", "message_type": "question", "suggestions": ["北京", "上海", "广州", "成都", "深圳", "其他"]}

event: step_start
data: {"step": "info_collection", "label": "正在了解您的出行需求..."}

event: progress
data: {"percent": 15, "message": "已获取出发地信息"}

// ... 多轮追问后进入规划阶段

event: step_start
data: {"step": "parallel_planning", "label": "正在为您规划行程..."}

event: progress
data: {"percent": 30, "message": "景点筛选完成，为您推荐了6个景点"}

event: progress
data: {"percent": 50, "message": "交通方案对比中，找到最优路线"}

event: step_end
data: {"step": "parallel_planning"}

event: step_start
data: {"step": "route_optimization", "label": "正在优化行程路线..."}

event: done
data: {"plan_run_id": "run_20260706_abc", "plan_id": "run_20260706_abc", "session_id": "sess_20260706_abc", "summary": {"destination": "大理", "days": 3, "daily_itinerary": [...], "budget": {...}}}
```

`plan_id` 是一轮兼容别名，与 `plan_run_id` 相同，均指向 `conversation_plan_runs`，
不是 `plans` 表主键。任一持久化步骤失败时只返回 `error` 事件，不返回 `done`。

### 4.6 SSE 持久化状态恢复

```
GET /api/v1/chat/sessions/{sessionId}/stream
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lastEventId` | string | 否 | 仅为兼容保留，当前不用于事件级续传 |

**恢复行为**：
- 使用与其他会话接口一致的 JWT 或 `X-Session-Id` 身份校验。
- 会话已完成时，从 `conversation_plan_runs` 返回最新方案的 `done` 事件。
- 会话未完成时返回 `resume_not_available` 错误事件，不会重新启动规划。

**心跳**：
- 服务端每 30 秒发送一行 `: keepalive`（SSE 注释行）
- 客户端 45 秒内未收到任何事件判定连接断开

**响应**：同上 SSE 流

### 4.7 获取消息历史

#### 分页翻页（首次加载）

```
GET /api/v1/chat/sessions/{sessionId}/messages?page=1&page_size=50
```

**响应体 `data`**：

```json
{
  "list": [
    {
      "id": "msg_001",
      "session_id": "sess_20260706_abc",
      "role": "user",
      "content": "我想去大理玩3天",
      "message_type": "text",
      "metadata": {},
      "created_at": "2026-07-06T14:30:00+08:00"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

#### 游标翻页（滚动加载更早历史）

```
GET /api/v1/chat/sessions/{sessionId}/messages?before_id=msg_010&limit=20
```

**响应体 `data`**：

```json
{
  "list": [
    {
      "id": "msg_009",
      "session_id": "sess_20260706_abc",
      "role": "user",
      "content": "我想去大理玩3天",
      "message_type": "text",
      "metadata": {},
      "created_at": "2026-07-06T14:30:00+08:00"
    }
  ],
  "has_more": true,
  "next_before_id": "msg_001"
}
```

#### 游标翻页（加载更新消息）

```
GET /api/v1/chat/sessions/{sessionId}/messages?after_id=msg_010&limit=20
```

**响应体 `data`**：

```json
{
  "list": [],
  "has_more": true,
  "next_before_id": null,
  "next_after_id": "msg_030"
}
```

`page` 不得与任一游标同时提交，`before_id` 和 `after_id` 也不得同时提交。
未提供分页参数时默认使用第 1 页。未知游标或其他会话的消息 ID 返回
`400 / code=10001`。

**Message 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 消息 ID（单调递增，可用于游标翻页） |
| `session_id` | string | 所属会话 ID |
| `role` | enum | `user` / `assistant` / `system` |
| `content` | string | 消息内容 |
| `message_type` | enum | `text` / `question` / `plan_progress` / `plan_result` |
| `metadata` | object | 附加数据：`text`/`question` 时含 `suggestions[]`；`plan_result` 持久化 `plan_run_id`，历史 API 根据该 ID 动态注入 `summary` |
| `created_at` | string | ISO 8601 时间戳 |

### 4.7 获取会话内方案生成记录

```
GET /api/v1/chat/sessions/{sessionId}/plans
```

**说明**：返回同一对话会话中已经生成过的方案摘要，按会话内生成序号倒序排列。该接口用于会话上下文、历史方案切换和前端列表展示，不替代正式方案详情接口。

**响应体 `data`**：

```json
[
  {
    "id": "run_20260709_002",
    "destination": "杭州",
    "days": 2,
    "summary": {
      "destination": "杭州",
      "origin": "上海",
      "days": 2,
      "trip_config": {
        "total_budget": 3000,
        "reserve_budget": 300,
        "planning_budget": 2700,
        "preferences": ["美食"],
        "preferences_provided": true
      }
    },
    "created_at": "2026-07-09T14:30:00+08:00"
  }
]
```

### 4.8 接口汇总

| 方法 | 路径 | 说明 | 鉴权 | 请求体 | 响应 |
|------|------|------|------|--------|------|
| POST | `/chat/sessions` | 创建新会话 | 可选 | `{ title? }` | JSON |
| GET | `/chat/sessions` | 会话列表 | 是 | `?page&page_size` | JSON（翻页） |
| PATCH | `/chat/sessions/{sessionId}` | 更新标题或置顶状态 | 是 | `{ title?, pinned? }` | JSON |
| DELETE | `/chat/sessions/{sessionId}` | 删除会话 | 是 | — | JSON |
| POST | `/chat/sessions/{sessionId}/messages` | 发送消息 | 可选 | `{ content }` | **SSE 流** |
| GET | `/chat/sessions/{sessionId}/stream` | SSE 连接（断点续传） | 可选 | `?lastEventId` | **SSE 流** |
| GET | `/chat/sessions/{sessionId}/messages` | 获取消息历史 | 是 | `?page&page_size` 或 `?before_id&limit` | JSON（翻页/游标） |
| GET | `/chat/sessions/{sessionId}/plans` | 获取会话内方案生成记录 | 是 | — | JSON |

---

## 五、方案接口

### 5.1 获取方案列表

```
GET /api/v1/plans?page=1&page_size=20&status=completed
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码，默认 1 |
| `page_size` | int | 否 | 每页条数，默认 20，最大 100 |
| `status` | string | 否 | 筛选状态：`draft` / `completed` / `failed` |

**响应体 `data`**：

```json
{
  "list": [
    {
      "id": "plan_20260706_abc",
      "title": "大理3日深度游",
      "destination": "大理",
      "start_date": "2026-07-15",
      "end_date": "2026-07-17",
      "days": 3,
      "estimated_cost": 4230.00,
      "travel_style": "relaxed",
      "status": "completed",
      "is_favorite": false,
      "created_at": "2026-07-06T14:30:00+08:00"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

**PlanSummary 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 方案 ID |
| `title` | string | 方案标题 |
| `destination` | string | 目的地 |
| `start_date` | string | 开始日期 |
| `end_date` | string | 结束日期 |
| `days` | int | 天数 |
| `estimated_cost` | number | 预估总费用 |
| `travel_style` | string | 旅行风格 |
| `status` | string | `draft` / `completed` / `failed` |
| `is_favorite` | boolean | 是否收藏 |
| `created_at` | string | 创建时间 |

### 5.2 触发方案生成

```
POST /api/v1/plans
```

**请求体**：

```json
{
  "session_id": "sess_20260706_abc",
  "confirmed": true
}
```

**响应**：**SSE 流**（同 4.4 节 SSE 事件序列）

`confirmed` 表示用户已经确认本轮旅行参数。未传或为 `false` 时，接口只返回等待确认的 `message` 和 `done` 事件，不启动完整规划：

```
event: message
data: {"role": "assistant", "content": "请先确认旅行参数，确认后我再开始生成完整方案。", "message_type": "text", "suggestions": ["确认，开始规划", "我想再改一下"]}

event: done
data: {"status": "waiting_confirmation"}
```

### 5.3 获取方案详情

```
GET /api/v1/plans/{planId}
```

**响应体 `data`**：PlanDetail 结构（见下方完整定义）

#### PlanDetail 完整结构

```json
{
  "id": "plan_20260706_abc",
  "title": "大理3日深度游",
  "destination": "大理",
  "departure": "北京",
  "start_date": "2026-07-15",
  "end_date": "2026-07-17",
  "days": 3,
  "people_count": 2,
  "crowd_type": "couple",
  "total_budget": 5000.00,
  "estimated_cost": 4230.00,
  "travel_style": "relaxed",
  "status": "completed",
  "version": 1,
  "is_favorite": false,
  "view_count": 0,

  "overview": {
    "highlights": ["洱海骑行", "古城漫步", "白族美食"],
    "total_distance_km": 120,
    "transport_modes": ["flight", "taxi", "bike"]
  },

  "daily_itinerary": [
    {
      "day": 1,
      "date": "2026-07-15",
      "date_label": "周三",
      "weather_summary": "晴，22-28°C",
      "activities": [
        {
          "time_slot": "08:00-10:00",
          "type": "transport",
          "title": "北京 → 大理",
          "subtitle": "CA1234 航班",
          "description": "首都T3 → 大理凤仪机场",
          "location": { "lat": 25.123, "lng": 100.234 },
          "cost": 1200.00,
          "tips": "建议提前2小时到达机场"
        },
        {
          "time_slot": "10:30-12:00",
          "type": "attraction",
          "title": "大理古城",
          "subtitle": "免费 · 步行游览",
          "description": "南诏国古都，感受白族建筑与历史文化",
          "location": { "lat": 25.678, "lng": 100.156 },
          "duration_minutes": 90,
          "cost": 0,
          "rating": 4.5,
          "tags": ["history", "culture", "photo"],
          "tips": "建议清晨前往，游客较少"
        },
        {
          "time_slot": "12:00-13:30",
          "type": "food",
          "title": "段公子·大理古国主题餐厅",
          "subtitle": "滇菜 · 人均¥80",
          "description": "招牌菜：大理砂锅鱼、乳扇",
          "location": { "lat": 25.679, "lng": 100.157 },
          "cost": 160.00,
          "rating": 4.3,
          "tags": ["local_cuisine", "must_eat"],
          "tips": "建议提前预约，高峰期需排队"
        }
      ],
      "accommodation": {
        "hotel_name": "大理古城·漫心酒店",
        "address": "大理古城人民路168号",
        "room_type": "大床房",
        "price": 380.00,
        "rating": 4.6,
        "check_in": "15:00",
        "check_out": "12:00",
        "location": { "lat": 25.681, "lng": 100.155 }
      },
      "day_cost": 1790.00,
      "day_summary": "上午抵达大理，游览古城；下午洱海骑行；夜宿古城"
    }
  ],

  "traffic_summary": {
    "city_to_city": [
      {
        "mode": "flight",
        "from": "北京",
        "to": "大理",
        "price": 1200,
        "duration": "3.5h",
        "recommendation": "推荐"
      }
    ],
    "city_internal": "建议使用网约车+骑行组合"
  },

  "food_summary": {
    "recommended_restaurants": [
      {
        "name": "段公子",
        "cuisine": "滇菜",
        "avg_price": 80,
        "rating": 4.3,
        "recommended_dishes": ["大理砂锅鱼", "乳扇"]
      }
    ],
    "total_food_budget": 600.00
  },

  "budget_detail": {
    "total": 4230.00,
    "breakdown": {
      "transport": { "amount": 1350.00, "percent": 32, "items": [{"name": "机票(往返)", "cost": 1200}, {"name": "市内交通", "cost": 150}] },
      "accommodation": { "amount": 1140.00, "percent": 27, "items": [{"name": "住宿(2晚)", "cost": 1140}] },
      "food": { "amount": 600.00, "percent": 14, "items": [{"name": "餐饮(3天)", "cost": 600}] },
      "attractions": { "amount": 340.00, "percent": 8, "items": [{"name": "景点门票", "cost": 200}, {"name": "租车", "cost": 50}] },
      "souvenirs": { "amount": 300.00, "percent": 7, "items": [] },
      "contingency": { "amount": 500.00, "percent": 12, "items": [] }
    }
  },

  "souvenir_recommendations": [
    {
      "name": "大理扎染",
      "description": "白族传统手工艺",
      "estimated_price": "50-200",
      "buy_place": "古城步行街"
    }
  ],

  "weather_forecast": [
    {
      "date": "2026-07-15",
      "weather": "晴",
      "temp_high": 28,
      "temp_low": 22,
      "wind": "微风",
      "humidity": 65,
      "precipitation": 0,
      "aqi": 45,
      "advice": "适合户外活动，注意防晒"
    }
  ],

  "packing_list": ["防晒霜", "墨镜", "薄外套", "运动鞋", "相机"],

  "tips": [
    "大理紫外线强，注意防晒",
    "尊重白族风俗习惯",
    "提前预订热门餐厅"
  ],

  "avoid_list": [
    "古城内拉客推销",
    "景区门口高价停车"
  ],

  "created_at": "2026-07-06T14:30:00+08:00",
  "updated_at": "2026-07-06T14:35:00+08:00"
}
```

#### Activity.type 枚举定义

| 枚举值 | 说明 | 图标色 |
|--------|------|--------|
| `transport` | 交通（航班/火车/打车等） | #1677ff 蓝 |
| `attraction` | 景点游览 | #52c41a 绿 |
| `food` | 美食/餐厅 | #fa8c16 橙 |
| `shopping` | 购物/纪念品 | #eb2f96 粉 |
| `rest` | 休息/自由活动 | #86909c 灰 |
| `entertainment` | 娱乐活动 | #f77234 橙红 |
| `accommodation` | 住宿 | #722ed1 紫 |

#### PlanDetail 字段说明

| 顶级字段 | 类型 | 说明 |
|---------|------|------|
| `overview` | object | 方案概览（亮点、总里程、交通方式汇总） |
| `daily_itinerary[]` | array | 每日行程（天级粒度，含活动和住宿） |
| `daily_itinerary[].activities[]` | array | 活动项 |
| `traffic_summary` | object | 城际交通 + 城内交通建议 |
| `food_summary` | object | 美食推荐汇总 + 餐饮预算 |
| `budget_detail` | object | 预算明细（总量 + 分类展开） |
| `souvenir_recommendations[]` | array | 纪念品推荐列表 |
| `weather_forecast[]` | array | 逐日天气预报（含 `humidity`、`precipitation`、`advice`） |
| `packing_list` | string[] | 行李清单建议 |
| `tips` | string[] | 实用贴士 |
| `avoid_list` | string[] | 避坑指南 |

### 5.4 局部修改方案

```
PATCH /api/v1/plans/{planId}
```

**说明**：使用 HTTP PATCH 方法进行局部更新，符合 RESTful 语义。请求体携带 `modifications` 描述变更内容。

**请求体**：

```json
{
  "modifications": [
    {
      "type": "replace_activity",
      "day": 1,
      "activity_index": 2,
      "target_type": "food",
      "reason": "换个口味",
      "constraints": {
        "cuisine": "chinese",
        "budget_per_person": 100
      }
    },
    {
      "type": "remove_activity",
      "day": 2,
      "activity_index": 3
    },
    {
      "type": "add_constraint",
      "constraint": "不要安排太紧凑的行程"
    }
  ]
}
```

#### Modification 类型说明

| type | 说明 | 必填字段 |
|------|------|---------|
| `replace_activity` | 替换某个活动项 | `day`, `activity_index`, `target_type`, `constraints` |
| `remove_activity` | 删除某个活动项 | `day`, `activity_index` |
| `add_constraint` | 添加新约束条件 | `constraint` |

**响应**：**SSE 流**

```
event: step_start
data: {"step": "modifying", "label": "正在调整行程..."}

event: progress
data: {"percent": 50, "message": "已为新替换的景点调整时间安排"}

event: step_end
data: {"step": "modify_complete"}

event: done
data: {"plan_id": "plan_20260706_abc", "updated_sections": ["day_1"]}
```

`updated_sections` 标识有变更的部分，前端据此局部刷新。

### 5.5 重新生成方案

```
POST /api/v1/plans/{planId}/generations
```

**请求体**：

```json
{
  "session_id": "sess_20260706_abc",
  "confirmed": true
}
```

**响应**：**SSE 流**。`confirmed=false` 时同 5.2 返回等待确认事件，不进入重新生成流程。

### 5.6 删除方案

```
DELETE /api/v1/plans/{planId}
```

**响应体 `data`**：`{}`

### 5.7 导出方案

#### 同步导出（Markdown）

```
POST /api/v1/plans/{planId}/exports?format=md
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 是 | `md` / `pdf` / `image` / `docx` |

**响应**（同步格式 `md` 直接返回文件）：
- Content-Type: `text/markdown`
- Content-Disposition: `attachment; filename="大理3日深度游.md"`

#### 异步导出（PDF / Image / Docx）

**请求**：
```
POST /api/v1/plans/{planId}/exports?format=pdf
```

**响应**（统一包装）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task_export_abc123",
    "status": "processing",
    "estimated_wait_seconds": 15
  },
  "request_id": "req_abc123"
}
```

**轮询任务状态**：

```
GET /api/v1/tasks/{taskId}
```

**响应**（处理中）：

```json
{
  "task_id": "task_export_abc123",
  "status": "processing",
  "progress": 60,
  "message": "正在渲染页面..."
}
```

**响应**（完成）：

```json
{
  "task_id": "task_export_abc123",
  "status": "completed",
  "download_url": "/api/v1/tasks/task_export_abc123/download",
  "expires_at": "2026-07-06T15:00:00+08:00"
}
```

**响应**（失败）：

```json
{
  "task_id": "task_export_abc123",
  "status": "failed",
  "error": {
    "code": 40005,
    "message": "方案导出失败，请稍后重试"
  }
}
```

前端轮询策略：每 2 秒查询一次，最多 30 次（60 秒超时）。

**下载文件**：

```
GET /api/v1/tasks/{taskId}/download
```

仅任务所有者可下载。任务未完成返回 HTTP 400 + `10001`；任务不存在、已过期、
不属于当前用户或文件不可用返回 HTTP 404 + `10003`。进程内任务产物完成后保留 1 小时。

**导出格式说明**：

| 格式 | 同步/异步 | Content-Type | 备注 |
|------|----------|-------------|------|
| `md` | 同步 | `text/markdown` | 直接返回 |
| `pdf` | 异步 | `application/pdf` | 通过 task 轮询 |
| `image` | 异步 | `image/png` | 通过 task 轮询 |
| `docx` | 异步 | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | 通过 task 轮询 |

### 5.8 分享方案

```
POST /api/v1/plans/{planId}/shares
```

**请求体**：

```json
{
  "expire_in": 86400,
  "password": "abc123"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `expire_in` | int | 否 | 过期时间（秒），不传则永不过期；建议选项：86400(1天) / 259200(3天) / 604800(7天) / 2592000(30天) |
| `password` | string | 否 | 访问密码，不传则公开访问 |

**响应体 `data`**：

```json
{
  "share_url": "https://travel.example.com/s/abc123",
  "expire_at": "2026-07-07T14:30:00+08:00"
}
```

### 5.9 收藏/取消收藏方案

```
POST /api/v1/plans/{planId}/favorites
```

**响应体 `data`**：

```json
{
  "is_favorite": true
}
```

多次调用为 toggle 操作。

### 5.10 接口汇总

| 方法 | 路径 | 说明 | 鉴权 | 请求体/参数 | 响应 |
|------|------|------|------|-------------|------|
| GET | `/plans` | 方案列表 | 是 | `?page&page_size&status` | JSON 翻页 |
| POST | `/plans` | 触发方案生成 | 是/匿名 | `{ session_id, confirmed }` | **SSE 流** |
| GET | `/plans/{planId}` | 方案详情 | 是/匿名 | — | JSON (PlanDetail) |
| PATCH | `/plans/{planId}` | 局部修改 | 是/匿名 | `{ modifications[] }` | **SSE 流** |
| POST | `/plans/{planId}/generations` | 重新生成 | 是/匿名 | `{ session_id, confirmed }` | **SSE 流** |
| DELETE | `/plans/{planId}` | 删除方案 | 是 | — | JSON |
| POST | `/plans/{planId}/exports` | 导出方案 | 是 | `?format=md | pdf | image | docx` | 文件下载 / JSON (task_id) |
| POST | `/plans/{planId}/shares` | 分享方案 | 是 | `{ expire_in?, password? }` | JSON |
| POST | `/plans/{planId}/favorites` | 收藏切换 | 是 | — | JSON |

---

## 六、基础数据接口

### 6.1 获取热门城市列表

```
GET /api/v1/data/cities?popular=true
```

**响应体 `data`**：

```json
[
  {
    "id": "city_001",
    "name": "大理",
    "province": "云南",
    "country": "中国",
    "name_en": "Dali",
    "longitude": 100.234,
    "latitude": 25.678,
    "level": "prefecture",
    "popular_rank": 12,
    "tags": ["历史名城", "自然风光", "休闲度假"],
    "image_url": "https://travel.example.com/images/dali.jpg",
    "description": "风花雪月，大理古城"
  }
]
```

### 6.2 搜索城市

```
GET /api/v1/data/cities?keyword=大理
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | string | 是 | 城市名称关键词 |

**响应体 `data`**：`City[]`

### 6.3 获取景点列表

```
GET /api/v1/data/attractions?city=大理&tags=自然&page=1&page_size=20
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `city` | string | 是 | 城市名称 |
| `tags` | string | 否 | 标签筛选，逗号分隔 |
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数 |

**响应体 `data`**：翻页 `Attraction[]`

**Attraction 结构**：

```json
{
  "id": "attr_001",
  "name": "大理古城",
  "city": "大理",
  "address": "大理市古城",
  "longitude": 100.156,
  "latitude": 25.678,
  "level": "5A",
  "rating": 4.5,
  "review_count": 35210,
  "ticket_price": "免费",
  "open_time": "全天开放",
  "suggest_duration": 120,
  "tags": ["历史", "文化", "拍照"],
  "best_time": "全年",
  "highlights": "南诏国古都，白族建筑群",
  "tips": "建议清晨前往，游客较少",
  "image_url": "https://..."
}
```

### 6.4 获取景点详情

```
GET /api/v1/data/attractions/{id}
```

**响应体 `data`**：`Attraction`

### 6.5 获取餐厅列表

```
GET /api/v1/data/restaurants?city=大理&cuisine=滇菜&page=1&page_size=20
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `city` | string | 是 | 城市名称 |
| `cuisine` | string | 否 | 菜系筛选 |
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数 |

**响应体 `data`**：翻页 `Restaurant[]`

**Restaurant 结构**：

```json
{
  "id": "rest_001",
  "name": "段公子·大理古国主题餐厅",
  "city": "大理",
  "address": "大理古城人民路168号",
  "longitude": 100.157,
  "latitude": 25.679,
  "cuisine": "滇菜",
  "avg_price": 80.00,
  "rating": 4.3,
  "recommended_dishes": ["大理砂锅鱼", "乳扇"],
  "open_time": "11:00-21:00",
  "need_booking": true,
  "tags": ["local_cuisine", "must_eat"],
  "tips": "高峰期需排队，建议提前预约"
}
```

### 6.6 获取酒店列表

```
GET /api/v1/data/hotels?city=大理&price_range=200-500&page=1&page_size=20
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `city` | string | 是 | 城市名称 |
| `price_range` | string | 否 | 价格范围，如 `200-500` |
| `page` | int | 否 | 页码 |
| `page_size` | int | 否 | 每页条数 |

**响应体 `data`**：翻页 `Hotel[]`

**Hotel 结构**：

```json
{
  "id": "hotel_001",
  "name": "大理古城·漫心酒店",
  "city": "大理",
  "address": "大理古城人民路168号",
  "longitude": 100.155,
  "latitude": 25.681,
  "star_level": 4,
  "rating": 4.6,
  "price": 380.00,
  "room_types": ["大床房", "双床房", "家庭房"],
  "facilities": ["WiFi", "早餐", "停车场", "洗衣服务"],
  "tags": ["古城内", "交通便利", "性价比高"],
  "distance_to_center_km": 0.5
}
```

### 6.7 查询天气

```
GET /api/v1/data/weather?city=大理&date=2026-07-15
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `city` | string | 是 | 城市名称 |
| `date` | string | 否 | 日期（YYYY-MM-DD），不传返回 7 天预报 |

**响应体 `data`**：

```json
{
  "city": "大理",
  "forecasts": [
    {
      "date": "2026-07-15",
      "weather": "晴",
      "temp_high": 28,
      "temp_low": 22,
      "wind": "微风",
      "humidity": 65,
      "precipitation": 0,
      "aqi": 45,
      "advice": "适合户外活动，注意防晒"
    }
  ]
}
```

> **注意**：PlanDetail 中的 `weather_forecast` 字段与此接口保持一致的字段结构，确保前端在两种数据源间切换时无适配成本。

### 6.8 接口汇总

| 方法 | 路径 | 说明 | 鉴权 | 参数 |
|------|------|------|------|------|
| GET | `/data/cities?popular=true` | 热门城市 | 可选 | `?popular=true` |
| GET | `/data/cities` | 搜索城市 | 可选 | `?keyword` |
| GET | `/data/attractions` | 景点列表 | 可选 | `?city&tags&page&page_size` |
| GET | `/data/attractions/{id}` | 景点详情 | 可选 | — |
| GET | `/data/restaurants` | 餐厅列表 | 可选 | `?city&cuisine&page&page_size` |
| GET | `/data/hotels` | 酒店列表 | 可选 | `?city&price_range&page&page_size` |
| GET | `/data/weather` | 天气查询 | 可选 | `?city&date` |

---

## 七、运维与元信息接口

### 7.1 健康检查

```
GET /api/v1/health
```

**用途**：CI/CD 部署探活、负载均衡健康检查、运维监控。

**响应体**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "dependencies": {
      "postgresql": "connected",
      "redis": "connected",
      "llm_service": "available"
    }
  },
  "request_id": "req_health_abc123"
}
```

**HTTP 状态码**：
- 200：所有依赖正常
- 503：至少一个关键依赖异常（但不影响启动重试）

### 7.2 查询任务状态

```
GET /api/v1/tasks/{taskId}
```

**用途**：轮询异步任务（导出等）的执行状态。

**响应体 `data`**：

```json
// 处理中
{
  "task_id": "task_export_abc123",
  "type": "plan_export",
  "status": "processing",
  "progress": 60,
  "message": "正在渲染页面..."
}

// 完成
{
  "task_id": "task_export_abc123",
  "type": "plan_export",
  "status": "completed",
  "download_url": "/api/v1/tasks/task_export_abc123/download",
  "expires_at": "2026-07-06T15:00:00+08:00"
}

// 失败
{
  "task_id": "task_export_abc123",
  "type": "plan_export",
  "status": "failed",
  "error": {
    "code": 40005,
    "message": "方案导出失败，请稍后重试"
  }
}
```

**错误码**：

| code | 说明 |
|------|------|
| 10003 | 任务不存在、已过期或不属于当前用户 |
| 10001 | 下载时任务尚未完成 |

### 7.3 下载任务产物

```
GET /api/v1/tasks/{taskId}/download
```

返回任务对应的 PDF、PNG 或 DOCX 文件流。任务状态与文件只在当前服务进程内有效，
服务重启后原任务视为不存在。

### 7.4 接口汇总

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 否 |
| GET | `/tasks/{taskId}` | 查询异步任务状态 | 是（按任务归属鉴权） |
| GET | `/tasks/{taskId}/download` | 下载已完成任务产物 | 是（按任务归属鉴权） |

---

## 八、扩展说明

相比 architecture.md 中已有的接口定义，本规范做了以下**拓展补充**：

| # | 拓展项 | 详述 |
|---|--------|------|
| 1 | **SSE 事件协议细化** | 新增 `suggestions` 字段用于追问时携带快捷选项；新增 `redirect_url` 在 `done` 事件中引导前端跳转；补充完整**SSE 重连规范**（Last-Event-ID、指数退避、30s 心跳、最多 10 次重试） |
| 2 | **方案修改接口** | `PATCH /plans/{planId}` 使用 HTTP PATCH 方法进行局部更新；定义标准化的 `Modification` 结构，支持 `replace_activity` / `remove_activity` / `add_constraint` 三种操作 |
| 3 | **方案分享接口** | 新增分享链接生成能力，支持过期时间（预设 1/3/7/30 天）、密码保护两种安全控制 |
| 4 | **方案导出接口** | 格式参数扩展为 `md`(同步) / `pdf` / `image` / `docx`（异步）；补充异步 Task 轮询机制和完善的错误码 |
| 5 | **PlanDetail 消费模型** | 完整定义前端展示所需的嵌套结构；Weather 字段与 Weather API 对齐（追加 `humidity`、`precipitation`、`advice`）；Activity.type 枚举扩展至 7 种类型 |
| 6 | **消息类型字段** | 新增 `message_type` 枚举区分 `text` / `question` / `plan_progress` / `plan_result`，前端据此决定渲染方式 |
| 7 | **城市模型** | 拓展 `popular_rank`、`tags`、`image_url`、`description` 等展示字段 |
| 8 | **UserPreferences 模型** | 新增 `custom_agent_name`、`agent_personality`、`avoid_tags` 等个性化字段 |
| 9 | **消息历史游标翻页** | 补充 `before_id/after_id/limit` 游标翻页方式，解决实时追加数据时 page 翻页的重复/遗漏问题 |
| 10 | **限流规范** | 定义全局限流/用户级限流/IP 限流/短信接口限流四维限流策略，规范 `X-RateLimit-*` 和 `Retry-After` 响应头 |
| 11 | **短信接口安全约束** | 补充 60 秒间隔上限、每日 5 次上限、防刷图形验证码等安全约束 |
| 12 | **错误码扩展** | 补充验证码发送限制（20006/20007）、方案导出失败（40005/40006）、任务状态错误码（70001/70002） |
| 13 | **运维接口** | 新增 `GET /health` 健康检查和 `GET /tasks/{taskId}` 异步任务状态查询 |
| 14 | **匿名数据合并** | 新增 `POST /user/sessions/anonymous/merge` 接口，登录后将匿名会话数据合并到用户账号 |
