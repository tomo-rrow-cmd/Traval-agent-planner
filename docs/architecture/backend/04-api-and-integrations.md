# API 与第三方服务

## 1. 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { },
  "request_id": "req_abc123"
}
```

错误码示例：`0` 成功，`10001` 参数错误，`20001` 未登录，`20002` 权限不足，`50000` 服务器错误。

## 2. 已实现接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/auth/register` | 手机号密码注册 |
| POST | `/api/v1/auth/sms-codes` | 发送短信验证码 |
| POST | `/api/v1/auth/sessions` | 手机验证码/密码登录 |
| POST | `/api/v1/auth/tokens` | 刷新 Token |
| DELETE | `/api/v1/auth/sessions/current` | 登出 |
| GET | `/api/v1/chat/sessions` | 会话列表 |
| POST | `/api/v1/chat/sessions` | 创建会话 |
| DELETE | `/api/v1/chat/sessions/{id}` | 删除会话 |
| POST | `/api/v1/chat/sessions/{id}/messages` | 发送消息并返回 SSE |
| GET | `/api/v1/chat/sessions/{id}/messages` | 消息历史 |
| GET | `/api/v1/chat/sessions/{id}/stream` | SSE 重连占位 |
| POST | `/api/v1/plans` | 触发方案生成 SSE |
| GET | `/api/v1/plans` | 方案列表 (分页) |
| GET | `/api/v1/plans/{id}` | 方案详情 |
| PATCH | `/api/v1/plans/{id}` | 局部修改方案 SSE |
| POST | `/api/v1/plans/{id}/generations` | 重新生成方案 SSE |
| DELETE | `/api/v1/plans/{id}` | 删除方案 |
| POST | `/api/v1/plans/{id}/exports` | 导出方案 |
| POST | `/api/v1/plans/{id}/shares` | 分享方案 |
| POST | `/api/v1/plans/{id}/favorites` | 收藏方案 |
| GET | `/api/v1/user/profile` | 用户资料 |
| PUT | `/api/v1/user/profile` | 更新资料 |
| GET | `/api/v1/user/preferences` | 用户偏好 |
| PUT | `/api/v1/user/preferences` | 更新偏好 |
| GET | `/api/v1/data/cities` | 城市数据 |
| GET | `/api/v1/data/attractions` | 景点列表 |
| GET | `/api/v1/data/restaurants` | 餐厅列表 |
| GET | `/api/v1/data/hotels` | 酒店列表 |
| GET | `/api/v1/data/weather` | 天气占位 |
| GET | `/api/v1/tasks/{taskId}` | 任务状态占位 |

## 3. 契约 MVP 边界

- 短信验证码固定为 `123456`，真实短信发送和频控尚未接入。
- `POST /plans`、`PATCH /plans/{id}`、`POST /plans/{id}/generations` 返回稳定 SSE 占位流；对话消息发送已接入 Agent SSE 管线，但测试中使用 stub 验证协议。
- `md` 导出同步返回 Markdown 占位内容，`pdf/image/docx` 返回任务占位。
- `/data/weather` 当前不调用外部天气服务；真实天气由 Agent 工具和服务适配器预留。
- 默认离线测试使用 mock/stub，不触发真实 LLM、地图、天气、Chroma、美团 CLI 或 12306 网络。

## 4. 第三方服务

| 服务 | Key 位置 | 用途 | 状态 |
|------|----------|------|------|
| DeepSeek | `.env` → `DEEPSEEK_API_KEY` | 主 LLM | 已适配，需真实 Key |
| 高德地图 | `.env` → `AMAP_API_KEY` | POI/路径/天气 | 已适配，需真实 Key |
| 美团酒旅 | `.env` → `MEITUAN_TOKEN`，启动时同步到 `~/.config/meituan-travel/config.json` | 酒店/景点/行程查询 | 可选 `mttravel` CLI，需真实 Token |
| 12306 | 无需 Key | 火车票查询 | 可选网络数据源 |
| Chroma/BGE | `chroma_data/` + 本地模型缓存 | BGE-M3 Top-K 召回 + BGE reranker 重排 | 可降级 |
| 豆包 | `.env` → `DOUBAO_API_KEY` | 备选 LLM | 已保留适配器 |
| 通义千问 | `.env` → `QWEN_API_KEY` | 备选 LLM | 已保留适配器 |
