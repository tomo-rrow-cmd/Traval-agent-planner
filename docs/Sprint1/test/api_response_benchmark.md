# API 响应时长测试报告（含测试数据）

**测试时间**: 2026-07-15 10:03:01
  
**测试环境**: 本地开发服务器 (端口 8001)
  
**测试端点数**: 59
  
**认证方式**: Bearer JWT Token (password 模式登录)
  
**数据准备**: 通过 app repositories 直接播种方案/行程/签到/花费/游记

---


## 认证

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| POST | `/auth/sms-codes` | 🟢 200 | 413.0 | {"code":0,"message":"ok","data":{"expires_in":60,"retry_after":60,"need_captcha" |
| POST | `/auth/sessions` | 🟢 200 | 580.3 | {"code":0,"message":"ok","data":{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp |
| POST | `/auth/tokens` | 🟢 200 | 396.0 | {"code":20001,"message":"Refresh Token 无效或已过期","data":null,"request_id":"req_465 |
| DELETE | `/auth/sessions/current` | 🟢 200 | 358.4 | {"code":0,"message":"ok","data":{},"request_id":"req_bde414b70cb4"} |

## 聊天

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| POST | `/chat/sessions` | 🟢 200 | 359.3 | {"code":0,"message":"ok","data":{"id":"0e0d9a50-aab1-4906-9048-317f76715dbb","ti |
| GET | `/chat/sessions` | 🟢 200 | 396.0 | {"code":0,"message":"ok","data":{"list":[{"id":"0e0d9a50-aab1-4906-9048-317f7671 |
| PATCH | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb` | 🟢 200 | 371.0 | {"code":0,"message":"ok","data":{"id":"0e0d9a50-aab1-4906-9048-317f76715dbb","ti |
| POST | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb/messages` | 🟢 200 | 2230.6 | SSE_OK |
| GET | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb/messages` | 🟢 200 | 354.2 | {"code":0,"message":"ok","data":{"list":[{"id":"c1ffb8b1-750d-4f82-95a6-6c72a8a7 |
| GET | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb/plans` | 🟢 200 | 384.3 | {"code":0,"message":"ok","data":[],"request_id":"req_4b1bdd148e7c"} |
| GET | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb/stream?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwODE0Y2FhOC1jMjgwLTQxZWEtYmQ2Ny0xN2Y2YWE2YWU2ZjkiLCJpYXQiOjE3ODQwODA5NDEsImV4cCI6MTc4NDA4ODE0MSwidHlwZSI6ImFjY2VzcyIsInBob25lIjoiMTg4ZjI5MWQyNWUifQ.GMulf0BwgRzSlW5ETofgpkbl6Tvq-6l_7oLukRyVcQY` | 🟢 200 | 2011.3 | SSE_OK |
| DELETE | `/chat/sessions/0e0d9a50-aab1-4906-9048-317f76715dbb` | 🟢 200 | 351.7 | {"code":0,"message":"ok","data":{},"request_id":"req_9652dc8d21b8"} |

## 方案

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| POST | `/plans` | 🟢 200 | 0.2 | SSE_OK |
| GET | `/plans` | 🟢 200 | 359.2 | {"code":0,"message":"ok","data":{"list":[{"id":"c2d32b9e-8302-443c-910f-83398611 |
| GET | `/plans/c2d32b9e-8302-443c-910f-83398611c59c` | 🟢 200 | 357.7 | {"code":0,"message":"ok","data":{"id":"c2d32b9e-8302-443c-910f-83398611c59c","ti |
| PATCH | `/plans/c2d32b9e-8302-443c-910f-83398611c59c` | 🟢 200 | 0.1 | SSE_OK |
| POST | `/plans/c2d32b9e-8302-443c-910f-83398611c59c/generations` | 🟢 200 | 0.2 | SSE_OK |
| POST | `/plans/c2d32b9e-8302-443c-910f-83398611c59c/exports` | 🟢 200 | 368.8 | # 北京3日旅行方案  > 出发 | 总预算 ¥0 | 预估花费 ¥0  ## 预算明细 | 类别 | 预算 | 实际 | 状态 | |------|----- |
| POST | `/plans/c2d32b9e-8302-443c-910f-83398611c59c/shares` | 🟢 200 | 359.8 | {"code":0,"message":"ok","data":{"share_url":"https://travel.example.com/s/c2d32 |
| POST | `/plans/c2d32b9e-8302-443c-910f-83398611c59c/favorites` | 🟢 200 | 368.6 | {"code":0,"message":"ok","data":{"is_favorite":true},"request_id":"req_f2ebb5579 |

## 行程

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| GET | `/trips` | 🟢 200 | 374.5 | {"code":0,"message":"ok","data":{"list":[{"id":"878ee4e0-5a54-49e9-8468-f950fa4c |
| POST | `/trips` | 🟢 200 | 367.9 | {"code":0,"message":"ok","data":{"id":"1e89e3d2-c9df-4e35-ac1d-5a3e3ab1793c","pl |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502` | 🟢 200 | 366.0 | {"code":0,"message":"ok","data":{"id":"878ee4e0-5a54-49e9-8468-f950fa4c2502","pl |
| PATCH | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502` | 🟢 200 | 380.0 | {"code":0,"message":"ok","data":{"id":"878ee4e0-5a54-49e9-8468-f950fa4c2502","pl |
| PATCH | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502` | 🟢 200 | 373.1 | {"code":0,"message":"ok","data":{"id":"878ee4e0-5a54-49e9-8468-f950fa4c2502","pl |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/progress` | 🟢 200 | 365.4 | {"code":0,"message":"ok","data":{"trip_id":"878ee4e0-5a54-49e9-8468-f950fa4c2502 |
| POST | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/checkins` | 🟢 200 | 385.1 | {"code":0,"message":"ok","data":{"id":"317d5ea7-9181-4759-872c-7c5e7815b439","tr |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/checkins` | 🟢 200 | 363.7 | {"code":0,"message":"ok","data":{"list":[{"id":"317d5ea7-9181-4759-872c-7c5e7815 |
| POST | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/expenses` | 🟢 200 | 372.2 | {"code":0,"message":"ok","data":{"id":"a41c20ac-c54f-47e2-a933-ec862ee30e08","tr |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/expenses` | 🟢 200 | 374.8 | {"code":0,"message":"ok","data":[{"id":"fd381857-d951-48f1-a438-1d8406627b26","t |
| POST | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/adjustments/detect` | 🟢 200 | 2707.9 | {"code":0,"message":"ok","data":{"id":"f1f0caf2-f711-4fe8-9f6e-f451ba62f8b4","tr |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/adjustments` | 🟢 200 | 363.3 | {"code":0,"message":"ok","data":{"list":[{"id":"f1f0caf2-f711-4fe8-9f6e-f451ba62 |
| GET | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/reminder` | 🟢 200 | 2752.3 | {"code":0,"message":"ok","data":{"day":2,"reminder_text":"明天咱们继续嗨玩啦！上午首站直奔景点，记得8 |
| POST | `/trips/878ee4e0-5a54-49e9-8468-f950fa4c2502/photos/annotate` | 🟢 200 | 2758.3 | {"code":0,"message":"ok","data":{"photos":[{"url":"https://example.com/p.jpg","a |

## 数据

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| GET | `/data/cities` | 🟢 200 | 356.4 | {"code":0,"message":"ok","data":[{"id":"city_001","name":"大理","province":"云南","c |
| GET | `/data/cities?keyword=%E5%8C%97%E4%BA%AC` | 🟢 200 | 384.2 | {"code":0,"message":"ok","data":[],"request_id":"req_137e54091240"} |
| GET | `/data/attractions?city=%E5%8C%97%E4%BA%AC` | 🟢 200 | 366.6 | {"code":0,"message":"ok","data":{"list":[{"id":"68c4033d-7da2-48fa-ad6a-94bd5514 |
| GET | `/data/attractions/1` | 🟢 200 | 378.6 | {"code":0,"message":"ok","data":null,"request_id":"req_df9170426ff8"} |
| GET | `/data/restaurants?city=%E5%8C%97%E4%BA%AC` | 🟢 200 | 373.3 | {"code":0,"message":"ok","data":{"list":[{"id":"96412381-401d-48a0-9056-39ab50e4 |
| GET | `/data/hotels?city=%E5%8C%97%E4%BA%AC` | 🟢 200 | 377.9 | {"code":0,"message":"ok","data":{"list":[{"id":"0d26133b-f8d4-4c72-adea-6e660876 |
| GET | `/data/weather?city=%E5%8C%97%E4%BA%AC&date=2026-07-16` | 🟢 200 | 380.2 | {"code":0,"message":"ok","data":{"city":"北京","forecasts":[{"date":"2026-07-16"," |

## 运维

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| GET | `/health` | 🟢 200 | 17.8 | {"code":0,"message":"ok","data":{"status":"healthy","version":"1.0.0","uptime_se |
| GET | `/tasks/nonexistent` | 🟢 200 | 388.2 | {"code":0,"message":"ok","data":{"task_id":"nonexistent","status":"completed","file_url":"/tasks/nonexistent/download"} |
| GET | `/tasks/nonexistent/download` | 🟢 200 | 375.7 | {"code":0,"message":"ok","data":{"content":"# 旅行方案导出...","format":"markdown"} |

## 游记

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| GET | `/travelogues` | 🟢 200 | 387.7 | {"code":0,"message":"ok","data":{"list":[{"id":"58023397-6fc5-404c-86a2-8ba548d9 |
| POST | `/travelogues` | 🟢 200 | 6276.7 | {"code":0,"message":"ok","data":{"id":"34b49fb5-aaa3-43c2-9db8-d81574094ff8","tr |
| GET | `/travelogues/89478666-535b-450d-b4c1-c19d677edcc9` | 🟢 200 | 374.6 | {"code":0,"message":"ok","data":{"id":"89478666-535b-450d-b4c1-c19d677edcc9","tr |
| PATCH | `/travelogues/89478666-535b-450d-b4c1-c19d677edcc9` | 🟢 200 | 382.1 | {"code":0,"message":"ok","data":{"id":"89478666-535b-450d-b4c1-c19d677edcc9","tr |
| POST | `/travelogues/89478666-535b-450d-b4c1-c19d677edcc9/publish` | 🟢 200 | 348.5 | {"code":0,"message":"ok","data":{"id":"89478666-535b-450d-b4c1-c19d677edcc9","tr |
| GET | `/travelogues/materials` | 🟢 200 | 370.8 | {"code":0,"message":"ok","data":null,"request_id":"req_efed8d6d145d"} |
| POST | `/travelogues/materials/generate` | 🟢 200 | 2221.9 | {"code":0,"message":"ok","data":{"materials":[{"id":"7c8f746f-97dc-4e00-83c6-2fd |
| POST | `/travelogues/shares` | 🟢 200 | 354.9 | {"code":0,"message":"ok","data":{"id":"f9fadb3f-f077-44d8-b6f3-8f5653ae0dd0","us |
| GET | `/travelogues/shares/test_share_code` | 🟢 200 | 363.4 | {"code":0,"message":"ok","data":null,"request_id":"req_8fe8a68f49a9"} |
| DELETE | `/travelogues/89478666-535b-450d-b4c1-c19d677edcc9` | 🟢 200 | 361.5 | {"code":0,"message":"ok","data":{},"request_id":"req_1443dafc966c"} |

## 用户

| 方法 | 路径 | 状态码 | 响应时长(ms) | 备注 |
|------|------|--------|-------------|------|
| GET | `/user/profile` | 🟢 200 | 368.4 | {"code":0,"message":"ok","data":{"id":"0814caa8-c280-41ea-bd67-17f6aa6ae6f9","ph |
| PUT | `/user/profile` | 🟢 200 | 381.5 | {"code":0,"message":"ok","data":{"id":"0814caa8-c280-41ea-bd67-17f6aa6ae6f9","nickname":"测试用户"} |
| GET | `/user/preferences` | 🟢 200 | 353.1 | {"code":0,"message":"ok","data":{"travel_style":"balanced","budget_level":"cost_ |
| PUT | `/user/preferences` | 🟢 200 | 363.4 | {"code":0,"message":"ok","data":{"travel_style":"balanced","budget_level":"cost_ |
| POST | `/user/sessions/anonymous/merge` | 🟢 200 | 372.3 | {"code":0,"message":"ok","data":{},"request_id":"req_51d55413a274"} |

---

## 汇总统计

| 指标 | 值 |
|------|-----|
| 平均响应时长 | 642.1 ms |
| 中位响应时长 | 371.8 ms |
| 最慢接口 | 6276.7 ms |
| 最快接口 | 0.1 ms |
| 成功 (2xx) | 59 |
| 失败 (非2xx) | 0 |
| 跳过/异常 | 0 |

### 各模块平均响应时长

| 模块 | 平均时长(ms) | 端点数 | 成功率 |
|------|-------------|--------|--------|
| 认证 | 436.9 | 4 | 4/4 |
| 聊天 | 807.3 | 8 | 8/8 |
| 方案 | 226.8 | 8 | 8/8 |
| 行程 | 878.9 | 14 | 14/14 |
| 数据 | 373.9 | 7 | 7/7 |
| 运维 | 260.6 | 3 | 3/3 |
| 游记 | 1144.2 | 10 | 10/10 |
| 用户 | 367.7 | 5 | 5/5 |