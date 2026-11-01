
# AI 旅行规划师 — Agent 框架全览

## 一、架构总览

```text
用户 (CLI/API)
    │
    ▼
UserInteractionAgent  ← 自然对话 + 需求提取
    │
    ▼
┌─ 编排管线 ────────────────────────────────────────┐
│                                                    │
│  [并行] 景点 + 天气                                 │
│     ↓                                               │
│  [串行] 路线优化 (2-opt)                             │
│     ↓                                               │
│  [并行] 美食 + 住宿 (美团优先)                       │
│     ↓                                               │
│  [串行] 交通 → 预算 → 纪念品                         │
│     ↓                                               │
│  冲突检测 → 完整方案输出                             │
│                                                    │
└────────────────────────────────────────────────────┘
```

## 二、Agent 基类能力

写在 `[agents/base.py]`，所有 Agent 继承它，自带以下能力：

| 能力 | 方法 | 说明 |
| --- | --- | --- |
| LLM 调用 | `call_llm()` | 调 DeepSeek，自动 3 次指数退避重试（1.5s → 2.25s → 3.4s） |
| 工具调用 | `call_llm_with_tools()` | 调 DeepSeek Function Calling，同样带重试 |
| 工具执行循环 | `execute_tools()` | LLM → tool_call → 执行 → 结果回传 → LLM 再处理（最多 3 轮） |
| 工具注册 | `register_tool()` / `register_tools_from_registry()` | 从全局工具注册表按名注册 |
| 输出校验 | `validate_output()` | Pydantic Schema 校验，字段缺失时自动补默认值 |
| 上下文 | `context` property | PlanContext 对象，带版本追踪和变更日志 |

## 三、9 个 Agent

### 1. UserInteractionAgent — 对话+需求提取

| 项 | 内容 |
| --- | --- |
| 职责 | 自然语言对话，收集目的地/天数/预算/偏好 |
| 数据源 | DeepSeek（纯 LLM） |
| 关键逻辑 | 两次 LLM 调用：一次对话生成回复，一次结构化提取 JSON |
| 就绪判定 | destination + days + budget 三者齐全（或用户说"随意"）→ ready=true |
| 追问规则 | 用户说"穷/没钱"追问预算数字，说"懒"自动标记 pace=轻松 |

### 2. AttractionAgent — 景点规划

| 项 | 内容 |
| --- | --- |
| 职责 | 搜索景点 → 分配每天行程 → 写推荐理由 |
| 数据源 | Chroma RAG（BGE embedding）→ PostgreSQL 兜底 |
| 工具 | `search_attractions`（RAG 语义搜索） |
| LLM 职责 | 排序、筛选、分配到每天、写中文推荐语 |
| 输出 | daily_plan — 每天 2-5 个景点，带名称、理由、建议时长 |

### 3. FoodAgent — 美食推荐

| 项 | 内容 |
| --- | --- |
| 职责 | 搜索餐厅 → 每天分配午餐+晚餐 |
| 数据源 | Chroma RAG（BGE embedding）→ PostgreSQL 兜底 |
| 工具 | `search_restaurants` |
| LLM 职责 | 匹配菜系偏好、控制预算、靠近当天景点、写推荐理由 |
| 输出 | meal_plan — 每天 2 餐，带店名、人均价、理由 |

### 4. HotelAgent — 住宿推荐

| 项 | 内容 |
| --- | --- |
| 职责 | 搜索酒店 → 推荐最合适的 |
| 数据源 | 美团酒旅 Skill（优先）→ Chroma RAG（兜底） |
| 工具 | `meituan_travel`（美团 CLI）、`search_hotels`（Chroma） |
| 关键特点 | 美团返回真实预订价格 + 美团真实评分，无任何估算 |
| 输出 | hotel_plan — 推荐 2 家，带真实价、晚数、总价、来源标注 |

### 5. TrafficAgent — 交通规划

| 项 | 内容 |
| --- | --- |
| 职责 | 规划景点间的交通路线和时间 |
| 数据源 | 高德 direction API（transit 公交路径规划） |
| 工具 | `get_route` |
| 关键特点 | 有坐标→调高德真实路径，无坐标→Haversine 距离估算（标注"估算"） |
| 输出 | daily_traffic — 每天每段路线的时间、距离、花费、方式 |

### 6. BudgetAgent — 预算管理

| 项 | 内容 |
| --- | --- |
| 职责 | 预算拆分 + 费用汇总 + 超支预警 |
| 数据源 | 确定性算法（不调 LLM，D-004 决策） |
| 分配比例 | 住宿 35% / 交通 20% / 餐饮 20% / 门票 15% / 购物 10% |
| 输出 | 总预算 vs 实际花费、逐项余量、超支 warning |

### 7. WeatherAgent — 天气适配

| 项 | 内容 |
| --- | --- |
| 职责 | 获取天气预报 + 行程调整建议 |
| 数据源 | 高德天气 API（实时天气 + 7 天预报） |
| 工具 | `get_weather` |
| LLM 职责 | 分析天气对行程的影响、穿衣建议、雨天转移室内 |
| 输出 | 天气数据 + 1-3 条文字建议 |

### 8. RouteOptimizerAgent — 路线优化

| 项 | 内容 |
| --- | --- |
| 职责 | 优化每天景点游览顺序，减少总路程 |
| 数据源 | 确定性算法：2-opt 局部搜索 |
| 关键算法 | 贪心最近邻生成初始解 → 2-opt 边交换迭代改进 → 输出优化后顺序 |
| LLM 职责 | 仅生成文字优化效果说明，不参与计算 |
| 输出 | 优化前后对比（节省 km、节省时间）、LLM 出行建议 |

### 9. SouvenirAgent — 纪念品推荐

| 项 | 内容 |
| --- | --- |
| 职责 | 推荐目的地特产和纪念品 |
| 数据源 | DeepSeek（纯 LLM 知识） |
| LLM 职责 | 根据城市和预算生成特产列表、价格区间、购买地点 |
| 输出 | 5-8 个商品，带名称、类别、价格区间、购买地、推荐理由 |

## 四、工具系统

写在 `[agents/tools/tool_registry.py]`，全局注册表。

| 工具名 | 调用方式 | 数据来源 | 返回 |
| --- | --- | --- | --- |
| `search_attractions` | 异步函数 | Chroma BGE → PostgreSQL | 景点列表 + 语义相关度 |
| `search_restaurants` | 异步函数 | Chroma BGE → PostgreSQL | 餐厅列表 + 人均价 |
| `search_hotels` | 异步函数 | Chroma BGE + Amap 详情 | 酒店列表 + 价格（部分） |
| `get_weather` | 异步函数 | 高德天气 API | 实时天气 + 7 天预报 |
| `get_route` | 异步函数 | 高德 direction API | 路径、时间、距离、花费 |
| `meituan_travel` | 子进程 CLI | mttravel 美团酒旅 Skill | 酒店真实价格+评分、景点门票、行程 |

## 五、数据存储

| 数据库 | 用途 |
| --- | --- |
| PostgreSQL | 7 张表：users, plans, attractions(126条), restaurants(368条), hotels(474条), conversations, messages |
| Chroma | 3 个 collection：attractions, restaurants, hotels（BGE 512 维向量） |
| 缓存 | Embedding 查询内存缓存（500 条上限）、Redis（预留） |

## 六、对话持久化

| 表 | 字段 | 作用 |
| --- | --- | --- |
| conversations | id, title, status, destination, days | 每次规划一个会话 |
| messages | conversation_id, role, content, sequence | 每条消息有序存储 |

> **支持功能：** 新建会话自动保存、`--resume <id>` 恢复历史、`/list` 查看列表、超 30 条自动清理旧消息。

## 七、第三方服务

| 服务 | Key | 用途 | 状态 |
| --- | --- | --- | --- |
| DeepSeek | `sk-09df21...` | 主 LLM | ✅ |
| 高德地图 | `a2aa2193...` | POI/路径/天气 | ✅ |
| 高德天气 | 同高德 Key | 天气查询 | ✅ |
| 美团酒旅 | Token | mttravel CLI 真实价格 | ✅ |