# AI 禁飞区 — 禁止 AI 生成代码的区域

本文件划定项目中**不允许 AI 编码工具（Claude Code / Copilot / Cursor 等）直接生成代码的模块与函数**。
这些区域的代码必须由开发者手写。AI 工具可以**读取、解释和辅助分析**这些文件，但不得自动生成或修改其中的实现逻辑。

## 划定原则

涉及以下特征的代码属于禁飞区，须手写：
- 确定性计算（金额、时间、距离、排序、约束求解），不允许 LLM 引入计算错误
- 硬编码的阈值/门禁/断路器，必须显式可审计
- 状态机的分支/循环/终止条件，必须可推演

---

## 1. 行程规划的约束求解

| 文件 | 函数/位置 | 说明 |
|------|----------|------|
| `app/agents/decision_agent.py` | `run_round1()` — 每日景点截断 `attractions[:4]` | 硬上限，不依赖 LLM 判断 |
| `app/agents/decision_agent.py` | `run_round2()` — `recs[0]` 直接取最高通勤分 | 酒店选择不走 LLM |
| `app/agents/attraction_agent.py` | `_name_key()` | 景点名称标准化，纯字符串算法 |
| `app/utils/validator.py` | `per_person_per_day < 100` 拒绝规划 | 预算下限门禁 |

---

## 2. 冲突检测与自动调整策略

| 文件 | 函数/位置 | 说明 |
|------|----------|------|
| `app/orchestrator/nodes.py` | `_dedupe_daily_plan()` + `_normalize_attraction_name()` | 管线级两阶段去重（并行规划后 + R1 后） |
| `app/agents/traffic_agent.py` | `_route_stops()` — 午餐 ≤14:00、晚餐 ≤21:00 | 用餐时间约束 |
| `app/agents/traffic_agent.py` | `_dedupe()` / `_same()` — 名称 + 50m 距离 | 站点去重 |
| `app/orchestrator/conflict_detection.py` | `ConflictDetector` 全类 | 时间/位置/预算/营业时间四类检测 |
| `app/agents/food_agent.py` | `_name_key()` + `_attach_candidate_data()` | 餐厅名称标准化 + 模糊匹配回填坐标价格 |
| `app/agents/hotel_agent.py` | `_name_key()` | 酒店名称标准化 |

---

## 3. 预算超支的动态再分配

| 文件 | 函数/位置 | 说明 |
|------|----------|------|
| `app/agents/budget_agent.py` | `_dynamic()` — 基础比例 + 城市系数 + 偏好修正 | 预算分配公式（确定性算术） |
| `app/agents/budget_agent.py` | `run()` — `should_retry = 0 < over_pct <= 30 and retry < 2` | 重试闸门（硬断路器） |
| `app/agents/budget_agent.py` | `_adj()` — `hotel_budget ≥ 200`、`meal_budget ≥ 50`、酒店直降 2 星 | 参数调整硬地板 |
| `app/orchestrator/nodes.py` | `node_adjust_params()` + `route_after_budget()` | 预算→重试→adjust→重跑的循环路由 |

---

## 维护要求

- 修改禁飞区内的任何硬编码阈值、门禁条件或循环终止逻辑，须同步更新本文档的表格。
- 新增符合划定原则的手写模块时，在对应章节追加条目。
- 若已划定区域的代码被 AI 工具修改，须人工 review 每一行变更。
