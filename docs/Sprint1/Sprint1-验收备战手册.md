# Sprint 1 验收备战手册

> 验收四项：① 项目运行检查 (3 min) → ② 文档与规范审查 (5 min) → ③ 代码走查 (6 min) → ④ Bug 注入测试 (4 min)

---

## ① 项目运行检查（3 min）— 当前状态与演示策略

### 当前状态

| 检查项 | 状态 | 说明 |
|---|---|---|
| FastAPI app 加载 | ✅ 通过 | 66 条路由注册成功，导入零报错 |
| 服务层测试 (17个) | ✅ 17/17 passed | 0.38s 跑完 |
| API 契约测试 (38个) | ✅ 38/38 passed | 2.82s 跑完 |
| Agent 测试 (约40个) | ⚠️ 超时 | 需要 DeepSeek API key 且网络正常才能跑 |
| LLM 测试 / RAG 测试 | ⚠️ 需要 API key | 同上，依赖外部服务 |

### 演示策略

**方案 A（推荐）— 有网 + API key 可用**：
```bash
# 1. 启动后端
cd /home/tby/ai-travel-planning
python main.py
# 访问 http://localhost:8000/docs 展示 Swagger UI

# 2. 演示核心流程
# - POST /api/v1/auth/sms-codes → 发送验证码
# - POST /api/v1/auth/sessions → 验证码登录（固定 123456）
# - POST /api/v1/chat/sessions → 创建对话会话
# - POST /api/v1/chat/sessions/{id}/messages → 发消息，看 SSE 流式返回
#   在浏览器 Network 标签展示 text/event-stream
```

**方案 B（备用）— 离线/无 API key**：
```bash
# 跑测试证明代码正确性
python -m pytest tests/test_services.py tests/test_api.py -v

# 展示 Swagger UI（不需要联网）
python main.py
# → http://localhost:8000/docs

# 即使 LLM 不可用，注册/登录/会话管理等接口仍然可用
```

**方案 C（快速演示脚本）**：
```bash
# 用 curl 演示核心流程
# 1. 获取验证码
curl -X POST http://localhost:8000/api/v1/auth/sms-codes \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800001111"}'

# 2. 登录
curl -X POST http://localhost:8000/api/v1/auth/sessions \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800001111","method":"phone","code":"123456"}'
# → 返回 access_token + refresh_token

# 3. 用 token 访问受保护接口
curl http://localhost:8000/api/v1/user/profile \
  -H "Authorization: Bearer <access_token>"
```

---

## ② 文档与规范审查（5 min）— 文档清单与关键内容

### 文档全景

| 目录 | 核心文档 | 用于回答什么问题 |
|---|---|---|
| `docs/architecture/` | [架构设计说明书.md](../architecture/架构设计说明书.md) | "你的系统架构是什么？" |
| `docs/architecture/backend/` | [01-概览与数据层](../architecture/backend/01-overall-and-data.md) → [07-路由解析](../architecture/backend/07-api-routes-analysis.md) | "后端怎么组织的？" |
| `docs/decisions/` | [01-架构基础](../decisions/01-architecture-foundation.md) → [05-持久化与前端](../decisions/05-persistence-frontend.md) | "为什么这样设计？" |
| `docs/api/` | [API接口规范文档.md](../api/API接口规范文档.md) | "API 有哪些？" |
| `docs/reports/` | 每日提交报告 0707-0710 | "这周做了什么？" |
| `.agent/guardrails.md` | [AI 禁飞区](../../../.agent/guardrails.md) | "哪些代码是手写的？" |

### Git 提交记录（Sprint 1 期间）

老师会看 `git log`。Sprint 1 期间的核心线索：

```
Sprint 1 起点:  feature/service-layer 分支建立
Sprint 1 终点:  HEAD = 88aed91

关键节点:
a8fbc79  会话持久化 — 原子事务、行级锁与游标分页
5b2e6ab  API 契约测试
8cf92ac  合并队友分支 feature/chenmingjie
9e7569f  修复联调发现的4个问题
020698e  修复联调后续问题
cb356b9  文档更新 + SSE修复
88aed91  对齐全量 Agent 架构文档（最新）
```

**讲解话术**：
> "Sprint 1 我们主要完成了服务层重构、会话持久化、前后端联调。我负责的是后端 API 层和 Agent 编排，队友负责前端。我们通过 feature branch 协作，合并后一起联调修复。"

### AI 禁飞区 — 必考！

文件在 [.agent/guardrails.md](../../../.agent/guardrails.md)。

**核心概念**：AI 禁飞区是**禁止 AI 编码工具生成代码**的模块清单，不是运行时 LLM 约束。

**你必须能背出的禁飞区**：

| 类别 | 文件 | 关键函数 | 为什么手写 |
|---|---|---|---|
| 约束求解 | `decision_agent.py` | `run_round1()` 截断 `[:4]` | 硬上限，不能依赖 LLM |
| 约束求解 | `decision_agent.py` | `run_round2()` `recs[0]` | 直接取最高分，不走 LLM |
| 预算 | `budget_agent.py` | `_dynamic()` | 预算公式是确定性算术 |
| 预算 | `budget_agent.py` | `run()` 重试闸门 | `0 < over_pct <= 30 and retry < 2` |
| 冲突检测 | `conflict_detection.py` | 全类 | 时间/位置/预算/营业时间 |
| 去重 | `nodes.py` | `_dedupe_daily_plan()` | 两阶段去重需精确逻辑 |
| 交通 | `traffic_agent.py` | 用餐时间约束 `≤14:00 / ≤21:00` | 硬约束 |

**话术**：
> "AI 禁飞区是我们项目中**必须由开发者手写、不允许 AI 工具生成**的代码区域。划定原则有三条：确定性计算、硬编码阈值、状态机分支——这些如果交给 LLM 会引入不可控的计算错误。比如 budget_agent 的预算分配公式和重试闸门，跑偏了会算出错误的预算；decision_agent 的每日 4 景点硬上限，不能用 LLM 判断。"

---

## ③ 代码走查（6 min）— 逐行讲解要点

### 推荐走查路径（选你最有信心的文件）

**路线 A：从请求到响应（展示全链路理解力）**

```
用户发消息 POST /api/v1/chat/sessions/{id}/messages
  │
  ├─ chat.py L258-281: send_message()
  │   ├─ record_message() → 幂等性检查（client_message_id）
  │   ├─ _load_history() → 加载最近 50 条消息
  │   └─ sse_response(_agent_sse_events(...))
  │
  ├─ chat.py L107-194: _run_pipeline_events()
  │   ├─ 延迟导入 DeepSeekLLM + UserInteractionAgent
  │   ├─ ui.stream_response() → SSE 逐 token 流式对话
  │   ├─ 守卫: mode=="travel_planning" and ready and confirmed
  │   └─ run_pipeline() → 五阶段并行规划
  │
  ├─ chat.py L64-104: sse_response()
  │   ├─ asyncio.Queue(maxsize=1) → 背压控制
  │   ├─ keepalive: 15s 无事件 → ": keepalive\n\n"
  │   └─ _SSE_DONE 哨兵 → 退出循环
  │
  └─ orchestrator/pipeline.py: run_pipeline()
      └─ LangGraph StateGraph → 5 阶段 DAG
```

**路线 B：展示禁飞区代码（展示对手写代码的理解）**

推荐讲解 `budget_agent.py` 的三个核心函数：
- `_dynamic()` — 预算分配公式
- `run()` — 重试闸门 `should_retry = 0 < over_pct <= 30 and retry < 2`
- `_adj()` — 调整硬地板 `hotel_budget ≥ 200, meal_budget ≥ 50`

### 逐行讲解速查

你已经有 [06-backend-code-explanation.md](../architecture/backend/06-backend-code-explanation.md) 和 [07-api-routes-analysis.md](../architecture/backend/07-api-routes-analysis.md) 两份文档，涵盖了所有需要逐行讲解的内容。

**老师最可能挑的 5 个文件**：

| 排名 | 文件 | 为什么 | 准备 |
|---|---|---|---|
| 1 | `chat.py` | 核心入口、SSE 框架 | 07-api-routes-analysis.md §3 |
| 2 | `auth.py` | JWT 认证链 | 07-api-routes-analysis.md §2 |
| 3 | `budget_agent.py` | 禁飞区 + 重试逻辑 | guardrails.md §3 |
| 4 | `decision_agent.py` | 禁飞区 + 两轮决策 | guardrails.md §1 |
| 5 | `orchestrator/nodes.py` | 管线节点 | guardrails.md §2 |

### 老师可能的提问 & 你应该的回答

**Q: "这个 `maxsize=1` 是什么意思？"**
A: "这是 asyncio 队列的背压控制。生产者和消费者速度不匹配时，队列最多积压 1 个事件，防止内存爆炸。如果生产者太快会被 await queue.put() 阻塞住。"

**Q: "为什么要用 object() 做哨兵？"**
A: "`_SSE_DONE = object()` 是唯一对象，用 `is` 比较绝对不会误判。如果用 `None`，队列中可能合法地有 None 值。"

**Q: "为什么 Agent 要延迟导入？"**
A: "避免循环依赖。Agent 导入 LLM，LLM 可能依赖 config，而 config 在应用启动时加载。如果放在模块顶层 import，启动顺序不同会导致 ImportError。"

**Q: "client_message_id 为什么能保证幂等？"**
A: "数据库对 `(session_id, client_message_id)` 建了唯一索引。重复请求 insert 时违反唯一约束，ORM 层捕获后返回 `created=False`，直接跳过 pipeline 执行。"

---

## ④ Bug 注入测试（4 min）— 预判与防御

### Bug 注入的常见套路

老师一般不会注一个全新的、毫无关联的 Bug。通常是在已有代码上：
1. **改一个条件**：`and` 改 `or`，`<` 改 `>`
2. **删一行**：删除某个关键校验
3. **改一个参数值**：`maxsize=1` 改成 `maxsize=100`
4. **引入类型错误**：`None` 和 `0` 和 `""` 的区别

### 根据你的代码，最高风险的注入点

#### 注入点 1: auth.py — 验证码校验

```python
# L82: 老师可能把验证码改成空字符串或别的值
if request.code != "123456":
```
**调试思路**：
- 先 `print(request.code)` 看实际值
- 检查 `SmsCodeResult()` 返回的内容
- 如果不行，直接在 `/auth/sms-codes` 返回里打 log

#### 注入点 2: chat.py — 守卫条件

```python
# L159: 老师可能把 and 改成 or
if not (mode == "travel_planning" and ready and confirmed):
```
**影响**：条件变宽松或变严格，pipeline 要么不触发要么乱触发
**调试思路**：
- 在守卫前打印 `mode, ready, confirmed` 三个值
- 用 curl 发一条明确是旅行规划的消息，看这三个值分别是多少

#### 注入点 3: chat.py — 幂等性检查

```python
# L269: 老师可能去掉 created 的检查
if not created:
```
**影响**：每次请求都重新执行 pipeline，client_message_id 的幂等保护失效
**调试思路**：
- 同一个 client_message_id 发两次请求
- 第一次应该触发 pipeline，第二次应该返回 `idempotent_replay`

#### 注入点 4: budget_agent.py — 重试闸门

```python
# 老师可能改条件为 should_retry = True 导致无限循环
should_retry = 0 < over_pct <= 30 and retry < 2
```
**影响**：无限重试或永不重试
**调试思路**：
- 打印 `over_pct` 和 `retry` 的值
- 确认循环终止条件是否符合预期

#### 注入点 5: plan.py — 导出格式校验

```python
# L164: 老师可能删除 format not in 的校验
if format not in ("md", "docx", "pdf", "image"):
```
**影响**：任意 format 参数可能引发下游错误
**调试思路**：
- 用 `format=exe` 等非法值测试，看是哪里报错

#### 注入点 6: SSE — asyncio.Queue maxsize

```python
# L71: 老师可能改成 maxsize=1000 或移除
queue: asyncio.Queue = asyncio.Queue(maxsize=1)
```
**影响**：背压失效，内存可能堆积
**调试思路**：
- 发大量消息，观察内存使用

### 调试现场的标准操作流程

老师注 Bug 后，你需要有条理地展示调试过程：

```
第1步（10秒）：复现 Bug
  "我先复现一下这个 Bug..."
  → 运行相关代码，确认异常行为

第2步（30秒）：定位范围
  "这是一个 XXX 类型的问题（条件判断/参数值/类型错误）"
  → 用 print() 或 logger 在关键位置打桩

第3步（1分钟）：缩小范围
  "我怀疑问题在 XXX 函数/条件..."
  → 二分法注释代码，逐步缩小可疑区域

第4步（1分钟）：确认根因
  "问题就在这里 — 原来是 XXX 被改成了 XXX"
  → 指出具体行号和变更

第5步（30秒）：修复并验证
  → 改回来，重新运行，确认 Bug 消失
```

### 最重要的：展示思路 > 修复速度

老师考察的是**你的调试思维过程**，所以：
- 每步都要**说出你在想什么**
- 即使一时没找到，展示二分法排除的逻辑
- 不确定时大胆假设然后验证

---

## 附: 验收前一小时 Checklist

- [ ] `python -m pytest tests/test_services.py tests/test_api.py -v` 全部通过
- [ ] `python main.py` 能启动，访问 `/docs` 能看到 Swagger
- [ ] 能背出 3 个禁飞区核心函数 + 手写原因
- [ ] 能讲清楚一条请求的完整链路（HTTP → Router → Service → Agent → LLM → SSE → 返回）
- [ ] 打开 [chat.py](../../../app/api/v1/chat.py) 能快速找到 key lines
- [ ] 打开 [budget_agent.py](../../../app/agents/budget_agent.py) 能指出重试闸门
- [ ] 打开 [guardrails.md](../../../.agent/guardrails.md) 确认内容没被改
- [ ] `git log --oneline -10` 能讲出每条提交做了什么
- [ ] 准备好 `.env` 文件，确保 API key 可用（如需要演示 LLM 功能）
- [ ] 浏览器开两个 Tab：`/docs` + `localhost:5173`（前端）
