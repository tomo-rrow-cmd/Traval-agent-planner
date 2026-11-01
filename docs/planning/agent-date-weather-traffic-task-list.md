# Agent 日期、偏好、天气与交通链路任务清单

## 1. 目标

在不改变现有 LangGraph 主流程、不调整 FoodAgent 并行策略、不修改多人费用口径的前提下，完成以下链路修正：

- 用户必须明确确认旅游日期后才能启动规划。
- 同时支持 `start_date + days` 和 `start_date + end_date`。
- 日期区间与 `days` 冲突时必须追问用户，不静默覆盖。
- 补齐菜系偏好和交通偏好的生产、透传、消费、保存及重新规划继承。
- 让高德天气数据和天气影响因子完整作用于景点与交通规划。
- 让往返交通、每日行程日期和最终方案使用同一日期范围。

## 2. 已确认规则

### 2.1 日期规则

- `start_date` 是规划必填信息；用户未提供时必须追问，不能再默认明天后直接生成方案。
- 支持以下输入组合：
  - `start_date + days`：推导 `end_date`。
  - `start_date + end_date`：推导包含首尾的 `days`。
  - `start_date + end_date + days`：三者一致时接受，不一致时追问确认。
- 只提供 `end_date` 不足以开始规划，仍需追问 `start_date`。
- 日期统一使用 `YYYY-MM-DD` 字符串在 Agent、PlannerState、SSE summary 和 `trip_config` 中传递。
- 相对日期必须基于 Asia/Shanghai 当前日期转换，例如“下周五”先转换成明确日期再确认。
- 出发日期早于今天、结束日期早于开始日期、日期格式无效或行程超过 30 天时，不进入 pipeline。

### 2.2 兼容规则

- LangGraph 节点顺序保持不变。
- FoodAgent 继续与 AttractionAgent、HotelAgent 并行执行。
- 不修改多人门票、餐饮、酒店房间数和交通费用计算规则。
- 不重命名 `QWeatherService`、`qweather.py` 或现有天气公开方法。
- 已保存但没有日期、菜系或交通字段的旧方案仍可读取；重新规划时只追问缺失的必填日期。

## 3. 实施任务

### TASK-01：建立统一日期解析与校验能力

**状态：已完成**

**完成记录**

- 已新增统一日期解析与校验能力，并让 `validate_date_range()` 复用同一规则。
- 已补充固定当前日期的单元测试，覆盖日期推导、冲突、缺失、过去日期、反向日期、无效格式和 31 天超长。
- 验证：`tests/test_validator.py` 通过。

**目的**

集中处理日期格式、日期推导和冲突检测，避免 UserInteractionAgent、WeatherAgent 和 TrafficAgent 分别计算日期。

**工作项**

- 新增统一日期解析函数，输入 `start_date`、`end_date`、`days` 和当前日期。
- 输出规范化后的 `start_date`、`end_date`、`days`，或结构化错误原因。
- 使用包含首尾的天数规则：`days = end_date - start_date + 1`。
- 区分缺失、格式错误、过去日期、顺序错误、超长行程和字段冲突。
- 保留当前 `validate_date_range()` 的有效规则，避免出现两套不同校验结果。

**依赖**

- 无。

**验收标准**

- `2026-08-01 + 3天` 得到 `2026-08-03`。
- `2026-08-01 至 2026-08-05` 得到 5 天。
- `2026-08-01 至 2026-08-05 + 3天` 返回日期冲突。
- 缺少 `start_date` 返回明确的必填错误。
- 过去日期、反向日期、超过 30 天均返回对应错误。
- 日期解析单元测试不依赖测试执行当天，可注入固定当前日期。

---

### TASK-02：补齐用户参数抽取与规划确认

**状态：已完成**

**完成记录**

- 已扩展 `UserInteractionAgent` 抽取与确认链路，支持 `start_date`、`end_date`、`cuisine_preferences`、`preferred_transport`。
- 已在确认前执行统一日期解析，缺少出发日期、日期与天数冲突等情况会停留在 collecting 状态。
- 已分离旅行偏好和菜系偏好，并规范交通方式默认值与可识别值。
- 验证：`tests/test_agents.py -k 'user_interaction_agent'` 通过；`tests/test_agents.py -m 'not integration'` 通过。
- 备注：完整 `tests/test_agents.py` 会进入已标记 `integration` 的真实 RAG/Embedding 用例，运行很慢，暂不作为本任务阻塞项。

**目的**

让用户明确提供并确认日期、菜系偏好和交通方式，避免下游字段只有消费者没有生产者。

**工作项**

- 在 UserInteractionAgent 抽取结果中增加：
  - `start_date`
  - `end_date`
  - `cuisine_preferences`
  - `preferred_transport`
- 在分析提示中注入当前日期，要求相对日期输出为 ISO 日期。
- 将 `start_date` 加入规划必填项；缺失时优先追问出发日期。
- 使用 TASK-01 的日期解析结果推导 `end_date` 或 `days`。
- 日期与 `days` 冲突时返回 collecting 状态，并说明两个值各自代表的天数。
- 分离通用旅行偏好和饮食偏好：
  - 历史、人文、亲子、自然风光进入 `preferences`。
  - 川菜、粤菜、素食、清真、不吃辣进入 `cuisine_preferences`。
- 只有菜系偏好时也将 `preferences_provided` 设为 true。
- 交通方式规范为现有 TrafficAgent 可识别值；未明确交通方式时仍使用“地铁”。
- 在确认文案中展示日期范围、天数、菜系和交通方式。
- 用户在确认消息后补充或修改日期、菜系、交通方式时，不得误判为直接确认。

**依赖**

- TASK-01。

**验收标准**

- “8月10日从武汉去成都玩4天”生成 `start_date=2026-08-10`、`end_date=2026-08-13`。
- “8月10日至8月14日去成都”自动生成 5 天。
- “8月10日至14日玩3天”进入冲突追问，不进入 pipeline。
- 未提供日期时只追问日期，不提前生成方案。
- “喜欢历史文化，想吃川菜，尽量步行”分别进入三个正确字段。
- “确认，不过改成8月20日出发”不会沿用旧日期直接启动规划。

---

### TASK-03：补齐确认恢复与重新规划继承

**状态：已完成**

**完成记录**

- 已扩展确认文案与历史 `trip_config` 提取，完整恢复日期、菜系和交通方式，并兼容旧方案缺少新增字段。
- 已按字段实现“其他沿用”和显式覆盖：仅修改出发日期、返程日期或天数时会重新推导其余日期字段；菜系修改不会清空旅行偏好。
- 旧方案没有 `start_date` 时保持为空并进入日期追问，同时保留原预算和旅行偏好。
- 验证：TASK3 定向用例通过；与 TASK4 合并定向回归共 `121 passed, 4 deselected`。

**目的**

保证用户确认后、会话恢复后和“其他配置沿用”场景不会丢失新增字段。

**工作项**

- 扩展确认消息解析，恢复日期、菜系和交通方式。
- 扩展 `trip_config` 历史提取和字段存在性判断。
- “其他沿用”时继承日期、菜系和交通方式。
- 用户明确修改日期、菜系或交通方式时，仅覆盖对应字段。
- 旧方案缺少 `start_date` 时不伪造历史日期，而是进入日期追问。
- 通用偏好修改和菜系修改分别识别，避免“想吃川菜”清空历史景点偏好。

**依赖**

- TASK-02。

**验收标准**

- 用户确认后下一轮“确认，开始规划”能够恢复完整日期范围。
- “目的地改成大理，其他沿用”保留原日期、菜系和交通方式。
- “菜系改成粤菜，其他沿用”只修改菜系。
- 旧方案重新规划时会追问日期，但不会丢失原预算和旅行偏好。

---

### TASK-04：扩展 PlannerState、pipeline 和最终配置

**状态：已完成**

**完成记录**

- 已在 `PlannerState` 和 pipeline 初始状态中加入规范化日期，并在 LangGraph 启动前执行统一日期校验；非法日期只返回错误事件，不调用 `planner_graph.astream()`。
- 已规范菜系列表和交通方式，FoodAgent 不再用旅行偏好回退菜系条件。
- 已补齐 BudgetAgent 输入、最终方案顶层和 `trip_config` 的日期、节奏、酒店/餐饮预算、菜系及交通字段，预算重试只覆盖明确调整项。
- 验证：`tests/test_orchestrator_pipeline.py`、`tests/test_orchestrator_nodes.py`、`tests/test_budget_helpers.py`、`tests/test_agents.py -m 'not integration'` 共 `121 passed, 4 deselected`；相关 API 回归 `7 passed`。

**目的**

建立从交互结果到所有规划节点的统一状态契约，并修复 BudgetAgent 最终配置回退默认值的问题。

**工作项**

- 在 PlannerState 增加 `start_date` 和 `end_date`。
- pipeline 创建初始状态前执行统一日期校验，非法日期不得启动 LangGraph。
- 保留并规范化 `cuisine_preferences` 和 `preferred_transport`。
- `node_parallel_planning` 只传明确的 `cuisine_preferences`，不再回退整个 `preferences`。
- `node_budget` 补传：
  - `start_date`、`end_date`
  - `pace`
  - `hotel_star`、`hotel_budget`
  - `meal_budget`
  - `cuisine_preferences`
  - `preferred_transport`
- BudgetAgent 在顶层 final plan 和 `trip_config` 中保存日期、菜系和交通方式。
- 预算自动重试时保留日期、菜系、交通方式和其他未调整字段。

**依赖**

- TASK-01、TASK-02。

**验收标准**

- pipeline 初始状态中的日期与用户确认结果一致。
- 非法或冲突日期不会调用 `planner_graph.astream()`。
- “文化深度”不会作为 FoodAgent 菜系条件。
- 最终 `trip_config` 中的节奏、酒店预算和餐饮预算不再退回默认值。
- 预算重试前后日期完全一致。

---

### TASK-05：修正天气日期和部分预报合并

**状态：已完成**

**完成记录**

- `node_weather` 已改用 PlannerState 的规范化日期；WeatherAgent 会过滤异常日期，并以完整日期范围的中性影响为底，按日期覆盖真实影响。
- 部分高德预报会保留真实天气，缺失日期单独回退为中性影响；最终天气摘要同样按日期关联。
- 验证：天气、节点及高德定向回归通过，包含部分预报、异常日期和远期 fallback 场景。

**目的**

让 WeatherAgent 查询用户真实旅游日期，并保留高德能够提供的部分真实天气。

**工作项**

- `node_weather` 使用 PlannerState 中的 `start_date/end_date`。
- WeatherAgent 对规范化日期进行查询，不再由节点固定计算“明天”。
- 按日期合并真实天气影响和中性影响：
  - 有真实预报的日期保留真实影响。
  - 高德预报范围外的日期只补对应中性影响。
- 不再因 `weather_impact` 数量少于 `days` 而整体替换。
- 天气日期异常时跳过异常记录，不影响其他有效日期。
- 保持高德参数：实况 `extensions=base`，预报 `extensions=all`，天气城市使用 adcode。

**依赖**

- TASK-04。

**验收标准**

- 天气查询收到用户确认的日期范围。
- 五天行程只有前三天真实天气时，前三天为真实影响，后两天为中性影响。
- 远期日期没有高德预报时，pipeline 正常完成且天气状态为 fallback。
- 暴雨、高温等真实天气仍生成正确的步行可行性和交通减速因子。

---

### TASK-06：修正交通日期、高德参数和天气耗时

**状态：已完成**

**完成记录**

- TrafficAgent 已接收统一日期；往返火车票分别使用 `start_date/end_date`，旧调用缺失日期时保留原兜底。
- `AmapService.route_planning()` 已增加可选 `city` 参数，仅公交/地铁请求写入高德参数；市内、酒店通勤和枢纽路线均传入目的地。
- 高德成功路线已应用天气减速因子，费用和距离保持不变；首日枢纽路线使用首日天气，失败时继续使用本地估算。
- 验证：交通 Agent、地图服务、节点和同步辅助测试通过，覆盖日期、城市参数、中英文方式、暴雨过滤、耗时减速及失败兜底。

**目的**

让 TrafficAgent 使用统一日期，并确保天气影响真正进入高德路线结果。

**工作项**

- TrafficAgent 接收 `start_date/end_date`。
- 去程火车票使用 `start_date`，返程火车票使用 `end_date`。
- `AmapService.route_planning()` 增加可选 `city` 参数，仅公交/地铁请求携带。
- 市内路线、酒店通勤评估和枢纽到酒店路线传入目的地城市。
- 对高德成功返回的路线应用 `traffic_speed_factor`；费用和距离保持不变。
- 交通方式比较前统一处理中英文值。
- 首日枢纽到酒店路线使用首日天气影响。
- 保留路线查询失败时的现有本地估算兜底。

**依赖**

- TASK-04、TASK-05。

**验收标准**

- 往返火车票查询日期分别等于 `start_date/end_date`。
- 公交请求包含城市参数，步行和驾车请求保持兼容。
- 正常天气保留用户交通方式和高德原始耗时。
- 暴雨天气过滤步行，并按减速因子增加高德路线耗时。
- 高德查询失败时仍能返回现有估算结构。

---

### TASK-07：补齐每日日期和端到端回归测试

**状态：已完成**

**完成记录**

- 最终方案每天已写入连续的 `date/date_label`，并按日期注入天气；顶层、`trip_config`、SSE summary 和 ConversationPlanRun summary 保留日期、菜系与交通方式。
- LangGraph 仍保持酒店决策后执行完整交通规划，预算重试继续保留未调整配置。
- 定向回归：`165 passed, 5 deselected`；其余离线套件：`641 passed, 2 skipped, 8 deselected`。
- 备注：完整门禁中的既有 `tests/test_api_edges.py::test_delete_plan` 在本环境单独运行超过 160 秒仍永久等待，因此该无关文件未计入上述其余离线套件；本任务相关测试无失败。

**目的**

让最终方案、前端和持久化摘要能够展示并恢复真实旅游日期，同时验证原有流程未受破坏。

**工作项**

- 最终方案顶层写入 `start_date/end_date`。
- 为每天行程补充：
  - `date`: `YYYY-MM-DD`
  - `date_label`: `M月D日`
- Day 1 对应 `start_date`，最后一天对应 `end_date`。
- 验证 ConversationPlanRun summary 完整保存日期和新增偏好字段。
- 更新受影响的 Agent、pipeline、节点、天气和交通测试。
- 执行定向回归和现有非集成 Agent/API 测试。

**依赖**

- TASK-03、TASK-04、TASK-05、TASK-06。

**验收标准**

- 每日日期连续且与行程天数完全一致。
- 前端现有 `start_date/end_date/date_label` 字段无需改接口即可显示。
- 持久化后重新读取 summary，日期、菜系和交通方式不丢失。
- 图编排仍为酒店选择后执行完整交通规划。
- 天气服务失败、交通服务失败、预算重试等原有兜底路径仍可完成规划。
- 定向测试全部通过，现有非集成回归无新增失败。

## 4. 推荐实施顺序

1. TASK-01：统一日期工具。
2. TASK-02：交互抽取与确认。
3. TASK-03：确认恢复和历史继承。
4. TASK-04：状态与最终配置透传。
5. TASK-05、TASK-06：天气和交通可并行开发。
6. TASK-07：最终输出和整体回归。

## 5. 完成定义

以下条件全部满足后，本任务清单才可整体标记完成：

- 用户未确认 `start_date` 时不能启动规划。
- 日期、天数、天气、往返交通和每日行程使用同一日期范围。
- 菜系偏好和交通方式具备完整的生产、透传、消费、保存和继承链路。
- 高德部分天气不会被整批中性值覆盖。
- 天气影响能够改变交通方式选择和路线耗时。
- 原有 Agent 编排、预算重试和外部返回结构没有破坏性变化。
- 所有新增测试和相关回归测试通过。

## 6. 本轮不包含

- 多人费用放大规则。
- 酒店房间数计算。
- FoodAgent 改为等待景点规划完成。
- 用户资料页偏好自动注入规划。
- PhotoPlannerAgent 的生产接入。
- 数据库表结构迁移。
