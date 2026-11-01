# 前端-后端 API 一致性测试报告

**测试时间**：2026-07-09 12:13:58
**后端地址**：http://localhost:8000/api/v1
**测试用户**：13800000001

---

## TC1: 闲聊问候

**问题**："你好"
**会话 ID**：`2f6d9fe1-1035-4dbe-becd-d1bb57a31102`
**路径 B 耗时**：3.4s

### 路径 B - 原始 SSE 事件序列

| # | 事件类型 | 数据预览 |
|---|---------|---------|
| 1 | `step_start` | {"step": "chat", "label": "Extracting..."} |
| 2 | `message_delta` | {"role": "assistant", "content_delta": "你好", "message_type": "text", "sequence": 1} |
| 3 | `message_delta` | {"role": "assistant", "content_delta": "！", "message_type": "text", "sequence": 2} |
| 4 | `message_delta` | {"role": "assistant", "content_delta": "我来", "message_type": "text", "sequence": 3} |
| 5 | `message_delta` | {"role": "assistant", "content_delta": "帮你", "message_type": "text", "sequence": 4} |
| 6 | `message_delta` | {"role": "assistant", "content_delta": "规划", "message_type": "text", "sequence": 5} |
| 7 | `message_delta` | {"role": "assistant", "content_delta": "旅行", "message_type": "text", "sequence": 6} |
| 8 | `message_delta` | {"role": "assistant", "content_delta": "。", "message_type": "text", "sequence": 7} |
| 9 | `message_delta` | {"role": "assistant", "content_delta": "请问", "message_type": "text", "sequence": 8} |
| 10 | `message_delta` | {"role": "assistant", "content_delta": "你的", "message_type": "text", "sequence": 9} |
| 11 | `message_delta` | {"role": "assistant", "content_delta": "出发", "message_type": "text", "sequence": 10} |
| 12 | `message_delta` | {"role": "assistant", "content_delta": "城市", "message_type": "text", "sequence": 11} |
| 13 | `message_delta` | {"role": "assistant", "content_delta": "是", "message_type": "text", "sequence": 12} |
| 14 | `message_delta` | {"role": "assistant", "content_delta": "哪里", "message_type": "text", "sequence": 13} |
| 15 | `message_delta` | {"role": "assistant", "content_delta": "？", "message_type": "text", "sequence": 14} |
| 16 | `message` | {"role": "assistant", "content": "你好！我来帮你规划旅行。请问你的出发城市是哪里？", "message_type": "text"} |
| 17 | `step_end` | {"step": "chat"} |
| 18 | `done` | {"status": "waiting_input", "session_id": "2f6d9fe1-1035-4dbe-becd-d1bb57a31102"} |

### 路径 A - 模拟前端消息列表

| # | 类型 | 角色 | 内容摘要 |
|---|------|------|---------|
| 1 | `plan_progress` | system | Extracting... |
| 2 | `text` | assistant | 你好！我来帮你规划旅行。请问你的出发城市是哪里？ |

### 渲染验证

**[OK] 所有渲染检查通过**

### 一致性对比

- **状态**：[MATCH] 完全一致
- **事件数**（Path B）：18
- **消息数**（Path A）：2

---

## TC2: 简单旅行规划

**问题**："我想去北京玩3天"
**会话 ID**：`8c722b0e-be93-435f-b227-58fdcef1a80b`
**路径 B 耗时**：3.0s

### 路径 B - 原始 SSE 事件序列

| # | 事件类型 | 数据预览 |
|---|---------|---------|
| 1 | `step_start` | {"step": "chat", "label": "Extracting..."} |
| 2 | `message_delta` | {"role": "assistant", "content_delta": "请问", "message_type": "text", "sequence": 1} |
| 3 | `message_delta` | {"role": "assistant", "content_delta": "您", "message_type": "text", "sequence": 2} |
| 4 | `message_delta` | {"role": "assistant", "content_delta": "是从", "message_type": "text", "sequence": 3} |
| 5 | `message_delta` | {"role": "assistant", "content_delta": "哪个", "message_type": "text", "sequence": 4} |
| 6 | `message_delta` | {"role": "assistant", "content_delta": "城市", "message_type": "text", "sequence": 5} |
| 7 | `message_delta` | {"role": "assistant", "content_delta": "出发", "message_type": "text", "sequence": 6} |
| 8 | `message_delta` | {"role": "assistant", "content_delta": "呢", "message_type": "text", "sequence": 7} |
| 9 | `message_delta` | {"role": "assistant", "content_delta": "？", "message_type": "text", "sequence": 8} |
| 10 | `message` | {"role": "assistant", "content": "请问您是从哪个城市出发呢？", "message_type": "text"} |
| 11 | `step_end` | {"step": "chat"} |
| 12 | `done` | {"status": "waiting_input", "session_id": "8c722b0e-be93-435f-b227-58fdcef1a80b"} |

### 路径 A - 模拟前端消息列表

| # | 类型 | 角色 | 内容摘要 |
|---|------|------|---------|
| 1 | `plan_progress` | system | Extracting... |
| 2 | `text` | assistant | 请问您是从哪个城市出发呢？ |

### 渲染验证

**[OK] 所有渲染检查通过**

### 一致性对比

- **状态**：[MATCH] 完全一致
- **事件数**（Path B）：12
- **消息数**（Path A）：2

---

## 全局汇总

- **测试用例数**：2
- **测试时间**：2026-07-09 12:13:58
- **后端地址**：http://localhost:8000/api/v1
