# AI 反思日志 — Sprint 2

**作者：** 封杨威 | **周期：** 2026-07-06 至 2026-07-14

---

## 一、AI 帮我完成了什么

### 1. 数据链路断点追踪（5 层跨文件排查）

V2.0 景点输出缺 `category`/`tags`，AI 从 Chroma metadata → RAG `_build_candidates` → `_fallback_search` → backfill → Pydantic validate，逐层打印中间值定位到根因：`AttractionItem` schema 没有这两个字段，validate 时被 Pydantic 静默过滤。人类逐层 debug 至少 2 小时，AI 端到端追踪约 20 分钟。

### 2. 批量代码生成（Vision 接入 + 交通增强）

- `vision.py`（160 行）：Qwen-VL-Max 适配器，含 URL 自动转 base64、单图标注、多图偏好提取、批量封面评分
- `photo_planner_agent.py`（130 行）：照片到旅行方案 Agent
- `travelogue_agent.py` PhotoOrganizer 改造：Vision 优先看图 + 文本 LLM 兜底
- `traffic_agent.py` 交通信息增强：从只返回距离/时间/价格升级到提取地铁线路名、上下车站、换乘站数、实时路况、红绿灯数、过路费

### 3. 测试用例编写（50+ 用例）

- `test_sprint2_quality.py`：33 个边界场景测试，覆盖 15 个核心函数、9 大类极端输入
- `test_v2_execution.py`：TripAgent/AdjustAgent/TravelogueAgent 全链路测试
- `test_agents.py`：12 个 Agent 独立测试
- `test_orchestration.py`：LangGraph 8 节点编排全流程测试

### 4. 代码审查与架构重构

- `weather_agent.py`：发现 8 个问题（2 个高危崩溃点、3 个中危逻辑缺陷、3 个低危代码质量问题），全部修复
- `hotel_agent.run()` 圈复杂度 45 降到 6：提取三个子方法
- `_apply_inherited_fields` 圈复杂度 47 降到 14：拆为四个子方法

### 5. 重复性文档生成

- Sprint 2 周报（按模板六段式）
- 边界场景测试明细表（36 条 x 6 列）
- AI 禁飞区 guardrails.md
- V2.0 功能全景文档（8 个模块 x 30+ 文件索引）

---

## 二、AI 没帮上忙 / 做错了什么

### 1. 同一行代码反复改错——背靠背依赖感知弱

attraction_agent.py 的 `category`/`tags` 回填改了 4 次才正确：

| 第几次 | 改了什么 | 为什么没修好 |
|--------|----------|------------|
| 1 | `_fallback_search` 加了 `category` 字段 | 只加到候选字典，忘了回填列表 |
| 2 | 回填列表加了 `category`/`tags` | Pydantic `AttractionItem` schema 没这两个字段，validate 时静默过滤 |
| 3 | schema 加了字段 | 上一步编辑把回填的 for 循环体删掉了（空循环） |
| 4 | 补回循环体 | 终于全部对齐 |

AI 每次做局部替换时没意识到跨文件的连锁影响。**教训：跨文件数据链路修复要一口气列出所有关联点再批量改，不要一个一个改。**

### 2. `setdefault` 和 `=` 的区别——对环境变量机制的误解

AI 写了 `os.environ.setdefault("EMBEDDING_LOCAL_FILES_ONLY", "true")`，但因为 `.env` 文件已设了 `false`，`setdefault` 不覆盖已有值。结果每次启动都去连 HuggingFace 超时 90 秒。

**教训：需要强制覆盖环境变量时用 `os.environ["KEY"] = "value"` 而非 `setdefault`，且必须在 pydantic Settings 实例化之前设置。**

### 3. Qwen-VL API 连通性诊断——盲目试错

AI 前后试了 6 次才让 Vision API 通：改 model ID → 换 base URL → 试 trial 域名 → 试 base64 → 最终发现是百炼控制台没开通模型服务。AI 在诊断 API 连通性时倾向于"试不同的参数组合"而非"先检查账号权限/服务状态"。

**教训：API 调不通先检查：账号是否开通了该服务 > Key 是否正确 > 网络是否通 > 参数是否正确。**

### 4. dev 分支合并后 API 签名变更未感知

dev 分支合并后 `_estimate` 增加了 `weather` 参数，`PipelineCache` 的方法名从 `get/set` 变成了 `rag_get/rag_set`。AI 写的测试用例基于旧 API 直接硬编码期望值（`time_min == 20`），结果 5 个测试失败。

**教训：合并上游分支后必须先跑一遍现有测试确认 API 没变，再写新测试。测试期望值应该验证"合理范围"而非"精确值"，避免实现细节变化导致测试脆弱。**

### 5. 测试 key 名不匹配——dict 契约没有类型保障

测试脚本中多次传参 key 名与 Agent 代码不一致：
- `planned_at` vs `planned_time`
- `drift_minutes` vs `drift_min`
- `spent_so_far` vs `budget_spent`

项目所有 Agent 的 input_data 都是 `dict[str, Any]`，没有 TypedDict 或 Pydantic schema 约束。人类和 AI 都容易写错 key 名，而且错误只在运行时表现为"返回默认值"而非"报错"。

**教训：Agent 的输入应该用 TypedDict 或 Pydantic 定义，让 IDE 和类型检查器在写代码时就发现 key 名错误。**

---

## 三、踩过的坑

### 坑 1：Windows GBK 编码导致中文乱码

**现象：** 测试脚本输出中文时 `UnicodeEncodeError: 'gbk' codec can't encode character`

**根因：** Windows 终端默认 GBK 编码，Python 3 print 中文触发编码错误

**解决：** 所有脚本顶部加 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

**经验：** Windows 开发的第一个坑永远是编码。项目模板应该内置这段代码。

### 坑 2：Pydantic 静默过滤未定义字段

**现象：** 代码里 `attraction["category"] = "风景名胜"` 设置成功，但 validate 后字段消失

**根因：** Pydantic v2 默认 `extra='ignore'`（BaseModel 不保留额外字段），未在 schema 声明的字段被静默丢弃

**解决：** 在 `AttractionItem` 中显式添加 `category: Optional[str] = None`

**经验：** Pydantic 的字段过滤是"静默"的——不报错、不警告、不在日志里出现。排查时在 validate 前后各打一个 print 是唯一可靠的定位方式。

### 坑 3：HuggingFace 在中国大陆的网络超时

**现象：** `sentence_transformers` 每次初始化尝试连接 huggingface.co，超时重试 5 次，阻塞 90 秒

**根因：** 中国防火墙阻止对 huggingface.co 的直接访问

**解决：**
1. 模型下载：用 `HF_ENDPOINT=https://hf-mirror.com` 镜像
2. 运行时加载：设置 `EMBEDDING_LOCAL_FILES_ONLY=true` 跳过网络检查
3. 必须在所有 `from app.` import 之前设置环境变量

**经验：** 国内开发涉及 HuggingFace 模型的项目，第一件事就是把这两个环境变量写死。

### 坑 4：Chroma metadata 坐标缺失——rebuild 脚本没跟 seed 脚本对齐

**现象：** seed_poi.py 写入 Chroma 时带了 `latitude`/`longitude`，但 rebuild_vectors.py 重建后坐标全部丢失

**根因：** seed_poi.py 的 `_vectorize` lambda 写了坐标字段，但 rebuild_vectors.py 的 `_attraction_meta` 只写了 name/city/rating/price/tags，漏了 latitude/longitude。两个脚本的 metadata builder 是独立维护的，没有共享同一个定义。

**解决：** 给 rebuild_vectors.py 的三个 metadata builder 都补上 latitude/longitude/category 字段

**经验：** 同一份数据结构的序列化逻辑不应该在两个地方分别实现。应该抽一个公共函数两边调。

### 坑 5：`_same` 函数的 `or 0` fallback 导致坐标缺失站点被静默跳过

**现象：** 市内交通方案最后一段"回酒店"神秘消失

**根因：**
```python
# 修复前
def _same(a, b):
    return haversine_distance(
        a.get("latitude") or 0, a.get("longitude") or 0,
        b.get("latitude") or 0, b.get("longitude") or 0,
    ) < 0.05
```
两个缺坐标的站点 → 四个参数都是 `0` → `haversine(0,0,0,0) = 0 < 0.05` → 被判为同一站 → 跳过

**解决：** 任一方缺坐标就不做距离判重，只比较名称

**经验：** `or 0` 作为默认值的写法在坐标场景有语义问题——(0,0) 是大西洋上的一个真实点，不等价于"缺失"。应该用显式的 None 检查。

---

## 四、学到的经验

### 1. AI 编码的正确打开方式

| 适合交给 AI | 不适合交给 AI |
|------------|-------------|
| 写模板代码（API 适配器、测试框架） | 改跨文件的连锁 bug（漏改概率高） |
| 批量重命名/重构（提取方法、降低圈复杂度） | 调 API 连通性（不会检查账号权限） |
| 生成文档/表格/周报 | 理解业务逻辑的微妙语义 |
| 写测试用例（边界场景覆盖） | 判断"修好了没有"（需要人来验证） |
| 代码审查（扫出潜在问题） | 判断修复优先级（需要业务上下文） |

### 2. 有效提问模式

- **好**："帮我追踪 `category` 从 Chroma 到 final_plan 的完整路径，在每一层打印中间值"
- **好**："这个文件圈复杂度最高的 3 个函数是哪些？"
- **好**："把 `weather_agent.py` 里的异常处理缺口全找出来"
- **差**："修一下这个 bug"（太模糊，AI 倾向于做表面修复）
- **差**："帮我写个脚本"（没说明输入输出格式，AI 猜错了 key 名）

### 3. 项目架构改进方向

- **Agent input_data 加类型约束**：所有 `dict[str, Any]` 改成 TypedDict，消灭 key 名拼写错误
- **公共 metadata builder**：seed_poi 和 rebuild_vectors 共用一个 `build_attraction_metadata()` 函数
- **Windows 开发模板**：项目模板内置 UTF-8 编码设置和环境变量前置
- **CI 加 smoke test**：每次 push 自动跑一个最小管线用例，防止 API 签名变更静默破坏

### 4. Sprint 2 个人成长

| 维度 | Sprint 1 | Sprint 2 |
|------|----------|----------|
| 对 AI 的依赖方式 | "帮我写这个功能" | "帮我审查/重构/测试这个功能" |
| Debug 效率 | 手动 print 逐层排查 | AI 并行追踪 + 人验证 |
| 代码审查 | 没有系统方法 | 圈复杂度扫描 + 异常路径检查 |
| 测试习惯 | 功能跑通就算 | 边界场景覆盖 + 极端值验证 |
| 文档意识 | 事后补 | 边写边记 |

---

## 附录：关键数据

| 指标 | 数值 |
|------|------|
| 向 AI 提问次数 | 60+ |
| AI 生成代码行数 | ~3500 行 |
| AI 生成后经人工修正的行数 | ~200 行 |
| AI 做错的次数 | 5 次（同一问题反复 4 次 + API 诊断 6 次） |
| 最终通过测试 | 33/33 |
| Sprint 2 新增/修改文件 | 17 个 |
| 发现并修复的 Bug | 12 个 |
