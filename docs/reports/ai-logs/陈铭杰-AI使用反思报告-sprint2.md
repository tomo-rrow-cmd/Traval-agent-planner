# 前端 AI 使用反思报告

> 项目：AI旅行规划师（ai-travel-planning）
> 视角：前端开发负责人
> 时间跨度：2026-07-07 ~ 2026-07-14
> 报告日期：2026-07-15

---

## 一、概述

本报告站在**前端开发负责人**的视角，对项目前端（Vue 3 + TypeScript + Pinia）在开发过程中使用 AI 编码工具（Claude Code）的实践进行系统性反思。项目后端采用多智能体架构（LangGraph）驱动，前端则承担了 SSE 流式交互、AI 生成内容渲染、多 Agent 管线可视化、以及 V2.0 行程执行与游记生成等核心 AI 功能的落地。

### 1.1 前端代码规模

| 类别 | 数量 | 说明 |
|------|------|------|
| Vue 组件 | 40+ | 分布在 10 个目录 |
| Pinia Store | 7 个 | auth/chat/plan/trip/travelogue/preference/ui |
| API 封装文件 | 10 个 | http.ts + 9 个业务模块 |
| TypeScript 类型文件 | 10+ | types/ 目录 |
| 测试文件 | 5+ | test/ 目录 |
| 工具函数 | 5+ | utils/ + standalone/ |

### 1.2 AI 集成全景图

```
用户输入 → ChatInput ──→ chatStore.sendMessage()
                              │
                         fetch(SSE POST)
                              │
                    ReadableStream.getReader()
                              │
                    行协议解析（事件分发）
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   step_start/step_end    message/delta         done
        │                     │                     │
   plan_progress 消息    AI 文本气泡        方案 Markdown + 数据
   + planStore 进度      + suggestions        + normalizeSSESummary()
        │                     │                     │
        ▼                     ▼                     ▼
   ChatSessionPage       ChatMessage.vue       PlanPreview 面板
   (进度条动画)          (markdown-it 渲染)    (BlockRenderer/可视化)
```

---

## 二、AI 前端集成场景分析

### 2.1 SSE 流式聊天引擎（效果：★★★★☆）

**涉及文件：**
- [chatStore.ts](../frontend/src/store/chatStore.ts) — `sendMessage()` 第 406-535 行 + `handleSSEEvent()` 第 540-695 行
- [chat.ts](../frontend/src/types/chat.ts) — 7 种 SSE 事件类型定义，第 41-98 行
- [sseParser.ts](../frontend/src/utils/sseParser.ts) — 独立 SSE 协议解析器

**AI 生成的代码模式：**

这是前端与 AI 后端通信的核心通道。AI 生成了完整的 SSE 流消费逻辑：

```typescript
// chatStore.ts 第 448-473 行 — AI 生成的 fetch SSE 骨架
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const response = await fetch(
  `${API_BASE}/chat/sessions/${currentSessionId.value}/messages`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  },
)
```

```typescript
// chatStore.ts 第 488-516 行 — AI 生成的行协议解析
const decoder = new TextDecoder()
let buffer = ''
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n')
  buffer = lines.pop() ?? ''
  // ...event 和 data 字段提取...
}
```

**效果：** AI 一次性生成了完整的 SSE 行协议解析 + 事件分发框架，且对 RFC 规范实现正确（`event:` + `data:` + 空行终止符）。这在没有 AI 的情况下需要参考规范手动实现，大约节省 2-3 小时。

**问题：** 独立的 `SSEParser` 类（[sseParser.ts](../frontend/src/utils/sseParser.ts) 第 7-63 行）是完全可复用的，但 chatStore 中的 `sendMessage()` 使用了内联的行解析逻辑而非 SSAParser 类。这导致两套相似的 SSE 解析代码共存，增加了维护成本。AI 在生成 chatStore 时，没有"发现"已有工具类并复用——这是 AI 缺乏代码库全局感知的典型案例。

**反思：** AI 在"独立函数"上表现优秀，但"代码复用"意识薄弱。解决方案：在 prompt 中明确提示"检查 utils/ 目录下是否有可复用的工具类"。

---

### 2.2 多 Agent 管线可视化（效果：★★★★★）

**涉及文件：**
- [chatStore.ts](../frontend/src/store/chatStore.ts) — `WAITING_PROMPTS` 词库第 203-237 行，`handleSSEEvent` `step_start/step_end` 处理第 542-620 行
- [ChatMessage.vue](../frontend/src/components/chat/ChatMessage.vue) — `plan_progress` 类型气泡第 74-88 行
- [ChatSessionPage.vue](../frontend/src/views/ChatSessionPage.vue) — 流式生成动画状态第 202-216 行

**AI 生成的代码模式：**

AI 设计了一套完整的 Agent 步骤可视化方案：

```typescript
// chatStore.ts 第 203-237 行 — AI 设计的情景感知等待词库
const WAITING_PROMPTS: Record<string, string[]> = {
  chat: ['正在分析你的需求…', '让我想想…', '思考旅行方案中…'],
  fetch_weather: ['正在查询目的地天气…', '分析天气对行程影响…'],
  planning: ['正在规划行程…', '搜索最佳景点中…', '安排每日路线…'],
  default: ['请稍等…', '正在处理…'],
}
```

**效果：** 这是 AI 表现最好的场景之一。AI 不仅处理了 step_start/step_end 的事件映射，还设计了：
1. **多元化提示词池**：根据 step 名从不同池中随机选取，避免用户看到的提示词重复
2. **进度条动画**：通过 `step_end` 事件更新现有消息的状态而非追加新消息
3. **脉冲点动画 + 渐变条**：ChatSessionPage 第 202-216 行中的 `chat-session__streaming-bar` CSS 动画
4. **撤销逻辑**：`disconnectStream()` 通过 AbortController 实现用户主动取消

```typescript
// chatStore.ts 第 607-619 行 — AI 处理 step_end：更新现有消息而非新增
case 'step_end': {
  const stepMsg = [...messages.value]
    .reverse()
    .find((m) => m.role === 'system' && m.metadata?.step === d.step)
  if (stepMsg) {
    stepMsg.metadata = { ...stepMsg.metadata, completed: true }
  }
  break
}
```

**反思：** 这种"渐进式 UI"的设计本需要领域知识和 UI 经验，AI 一次性生成了完整方案。关键原因在于 prompt 中描述了"朋友感"和"旅行温度"的体验目标，AI 将其转化为具体的动画和文案设计。这说明**给 AI 明确的体验目标比给具体的 UI 指令更有效**。

---

### 2.3 SSE 数据归一化 — 后端异构数据适配（效果：★★★☆☆）

**涉及文件：**
- [planStore.ts](../frontend/src/store/planStore.ts) — `normalizeSSESummary()` 第 222-404 行
- [mapSSESummaryToPlan()](../frontend/src/store/planStore.ts) 第 205-216 行

**AI 生成的代码模式：**

这是前端最复杂的适配层：将后端 SSE `done` 事件的 summary 对象转换为前端 `PlanResponse` 格式：

```typescript
// planStore.ts 第 240-260 行 — AI 生成的字段映射
activities: rawActs.map((a: any) => ({
  time_slot: a.time_slot || '',
  type: a.type || 'attraction',
  title: a.name || a.title || '',           // name → title
  description: a.reason || a.description || '', // reason → description
  duration_minutes: a.duration_hours         // duration_hours → duration_minutes
    ? Math.round(a.duration_hours * 60) : undefined,
  // ...
})),
```

```typescript
// planStore.ts 第 302-315 行 — 中英文预算分类名兼容
function findCat(...names: string[]): number {
  for (const name of names) {
    const d = details.find((x: any) => x.category === name)
    if (d) return d.spent ?? d.budget ?? 0
  }
  return 0
}
const catMap = {
  transport: { label: '交通', names: ['交通', 'transport', 'traffic'] },
  accommodation: { label: '住宿', names: ['住宿', 'accommodation', 'hotel'] },
  // ...
}
```

**效果：** normalizeSSESummary() 约 180 行代码，处理了 5 类字段映射、3 层嵌套数据转换、2 种交通格式兼容、以及中英文预算分类名的兼容。AI 把这块逻辑一次跑通，调试成本极低。

**问题：** 存在两个功能重叠的函数：`mapSSESummaryToPlan()`（第 205 行，简洁版）和 `normalizeSSESummary()`（第 222 行，完整版）。前者在早期 commit 中出现但很快被后者取代。这说明 **AI 生成代码演进过程中会产生遗留代码**——AI 倾向于追加新模式而非重构旧代码，需要人工清理。

**关键教训：** normalizeSSESummary() 这种"对齐两个数据模型的胶水层"恰好是 AI 的强项，因为它的工作模式是**有明确输入输出的纯函数转换**，不需要理解业务语义。但如果后端字段名频繁变化（本项目确实如此），这块代码需要同步更新，AI 在跨文件一致性维护上需要人工提醒。

---

### 2.4 方案 Markdown 生成器（效果：★★★★☆）

**涉及文件：**
- [chatStore.ts](../frontend/src/store/chatStore.ts) — `generatePlanMarkdown()` 第 34-187 行
- [planMarkdown.ts](../frontend/src/utils/planMarkdown.ts) — 工具类 Markdown 生成器

**AI 生成的代码模式：**

```typescript
// chatStore.ts 第 34-187 行 — AI 生成 Markdown 模板
function generatePlanMarkdown(summary: Record<string, any>): string {
  const parts: string[] = []
  parts.push(`# 🗺️ ${tripName}`)
  parts.push(`**${origin ? origin + ' → ' : ''}${dest}** · **${days}天**`)
  // 对每一天的每一个景点渲染 markdown
  for (const day of itinerary) {
    parts.push(`## 📅 第${day.day}天`)
    for (const attr of attractions) {
      parts.push(`### ${attr.name}`)
      if (attr.reason) parts.push(`> ${attr.reason}`)
      // 标签渲染
      if (tagItems.length) parts.push(`> \`${tagItems.join('` \`')}\``)
    }
  }
  return parts.join('\n')
}
```

**效果：** AI 设计了一个纯字符串模板方案，没有使用任何模板引擎（如 Handlebars、EJS），而是利用 Array + join 构建输出。这个设计决策是正确的——避免引入额外依赖。生成的 Markdown 结构清晰，层级分明（h1 方案标题 → h2 每日行程 → h3 景点名称）。

**问题：** chatStore.ts 中的 `generatePlanMarkdown`（第 34-187 行）比 [planMarkdown.ts](../frontend/src/utils/planMarkdown.ts) 更完整，但后者是独立的工具类。AI 在两次不同的调用中生成了两个版本，导致功能重叠。更合理的结构应该是：工具类 `planMarkdown.ts` 包含核心逻辑，chatStore.ts 只做数据准备后调用工具类。

**反思：** AI 在工具函数组织上常见的问题是**不知道该放在哪个文件**。它倾向于把所有相关功能塞进 Store 文件，导致 Store 文件膨胀（chatStore.ts 746 行）。后续应该明确指导 AI："工具函数放 utils/，需要多个 Store 共同访问的方法放 composables/"。

---

### 2.5 内容块渲染系统（效果：★★★★★）

**涉及文件：**
- [BlockRenderer.vue](../frontend/src/components/plan/BlockRenderer.vue) — 内容块分发渲染
- [DayCard.vue](../frontend/src/components/plan/DayCard.vue) — 单日行程卡片

**内容块类型系统（由 AI 设计）：**

```typescript
export type ContentBlockType =
  | 'header' | 'day_card' | 'budget_chart' | 'map'
  | 'traffic_list' | 'highlights' | 'section' | 'text'
  | 'divider' | 'callout' | 'list'
```

**效果：** AI 设计的 ContentBlock 联合体是一个纯声明式的渲染方案。BlockRenderer 根据 `block.type` 分发到对应的子组件，扩展新块类型只需添加新类型 + 新组件，无需修改分发逻辑。这种模式是 AI 从设计系统领域迁移到业务 UI 的优秀案例。

**反思：** 这种基于联合类型的分发模式是 TypeScript 项目中 AI 最容易正确生成的模式——类型定义清晰、分支逻辑明确、没有副作用。AI 在这类"模式匹配"风格的代码上几乎不会出错。

---

### 2.6 V2.0 AI 功能接入（效果：★★★★☆）

#### 2.6.1 行程异常检测与调整

**涉及文件：**
- [tripStore.ts](../frontend/src/store/tripStore.ts) — `doDetectAnomalies()` 第 127-134 行
- [api/trip.ts](../frontend/src/api/trip.ts) — `detectAnomalies()` 第 163-171 行

```typescript
// tripStore.ts 第 127-134 行 — AI 生成的异常检测触发
async function doDetectAnomalies(triggerType: string, detail?: Record<string, unknown>) {
  if (!activeTrip.value) return
  const res = await detectAnomalies(activeTrip.value.id, {
    trigger_type: triggerType,
    trigger_detail: detail,
  })
  return res.data.data
}
```

**问题：** `doDetectAnomalies` 返回 `res.data.data`，没有在 Store 层持久化结果。调用方需要手动处理返回值的状态更新。这与 tripStore 中其他方法（如 `doCheckin` 自动更新 `checkins.value`）不一致。

**关键教训：** AI 在 Store 的规范化上容易出现**疏漏的一致性**——同一个 Store 中，大部分方法有状态更新侧效应，少数方法没有。需要人工 review 每个 Store action 的"是否有更新 Store state"的完整性。

#### 2.6.2 AI 游记与素材生成

**涉及文件：**
- [travelogueStore.ts](../frontend/src/store/travelogueStore.ts) — `generate()` 第 39-48 行，`generateAllMaterials()` 第 75-85 行
- [api/travelogue.ts](../frontend/src/api/travelogue.ts) — `generateTravelogue()` 第 66-68 行，`generateMaterials()` 第 88-89 行

```typescript
// travelogueStore.ts 第 39-48 行
async function generate(tripId: string, style: string = 'diary') {
  isGenerating.value = true
  try {
    const res = await generateTravelogue(tripId, style)
    current.value = res.data.data ?? null
    return current.value
  } finally {
    isGenerating.value = false
  }
}
```

**效果：** AI 为游记和素材生成提供了统一的 `isGenerating` 状态管理 + try/finally 模式。这个模式在 chatStore、planStore、travelogueStore 中保持了一致。

#### 2.6.3 照片 AI 标注

**涉及文件：**
- [api/trip.ts](../frontend/src/api/trip.ts) — `annotatePhotos()` 第 197-199 行

```typescript
export function annotatePhotos(tripId: string, checkin: Record<string, unknown>) {
  return http.post<ApiResponse<Record<string, unknown>>>(`/trips/${tripId}/photos/annotate`, { checkin })
}
```

---

### 2.7 测试模拟中的 AI 管线（效果：★★★★☆）

**涉及文件：**
- [test/mocks/chat.ts](../frontend/src/test/mocks/chat.ts) — `mockSSEEvents` 第 67-213 行，`createSSEStream()` 第 218-245 行

**AI 生成的代码模式：**

```typescript
// test/mocks/chat.ts 第 67-213 行 — AI 模拟的完整 Agent 管线
export const mockSSEEvents = [
  { event: 'step_start', data: { step: 'chat', label: '分析需求...' } },
  { event: 'message', data: { role: 'assistant', content: '...', message_type: 'text' } },
  { event: 'step_end', data: { step: 'chat' } },
  { event: 'step_start', data: { step: 'planning', label: '正在规划 大理 行程...' } },
  { event: 'progress', data: { percent: 10, message: '景点搜索中...' } },
  // ...更多进度事件
  { event: 'done', data: { plan_id: 'plan_mock001', summary: { ... } } },
]
```

```typescript
// test/mocks/chat.ts 第 218-245 行 — AI 生成的 ReadableStream 工厂
export function createSSEStream(events): ReadableStream<Uint8Array> {
  return new ReadableStream({
    async pull(controller) {
      if (index >= events.length) { controller.close(); return }
      const lines = [
        `id: evt_${index}\n`,
        `event: ${event}\n`,
        `data: ${JSON.stringify(data)}\n\n`,
      ]
      for (const line of lines) controller.enqueue(encoder.encode(line))
      await new Promise((r) => setTimeout(r, 10))
    },
  })
}
```

**效果：** AI 生成的测试 mock 与真实 SSE 流保持一致格式，包含完整的 3 阶段 Agent 管线模拟（chat → planning → done）。`createSSEStream()` 返回 `ReadableStream<Uint8Array>` 与真实 fetch Response.body 的类型一致，使得测试代码可以直接复用 ChatSessionPage 和 chatStore 的消费逻辑，无需修改。

**反思：** 这是"AI 写测试"的最佳实践——AI 生成的 mock 不是"测试数据"，而是"测试基础设施"。它让前端开发者可以在不依赖后端的情况下完成完整的流式交互测试。

---

## 三、关键问题与反思

### 3.1 代码复用不足（AI 的通病）

| 问题 | 具体表现 | 影响 |
|------|---------|------|
| 两套 SSE 解析 | `sseParser.ts` 类 vs chatStore 内联解析 | 代码冗余，维护成本翻倍 |
| 两个 Markdown 生成器 | `chatStore.ts` 第 34-187 行 vs `planMarkdown.ts` | 功能不一致，修改需同步 |
| 两个 SSE summary 转换函数 | `mapSSESummaryToPlan()` vs `normalizeSSESummary()` | 前者已被后者覆盖但未删除 |

**根因分析：** AI 在每次生成时以"当前 prompt 的上下文"为基准，不会自动扫描整个代码库寻找可复用工具。这导致同一个功能在不同时间、不同 prompt 下生成了多个版本。

**改进方案：** 
- 在 prompt 中明确指定"检查 utils/、composables/ 目录下是否有可复用方法"
- 人工在 code review 中发现重复代码时，通过 Claude 的修复命令（`/fix`）合并

### 3.2 Store 方法的一致性

AI 在生成 Store 方法时，对"副作用"的处理模式不统一：

| 方法 | 自动更新 Store state | 返回值 |
|------|---------------------|--------|
| `doCheckin()` | ✅ `checkins.value.unshift(c)` | return c |
| `doAddExpense()` | ✅ `expenses.value.unshift(e)` | return e |
| `doDetectAnomalies()` | ❌ 不更新 adjustments | return res.data.data |
| `doAcceptAdjustment()` | ❌ 不更新 adjustments | return res.data.data |

**根因分析：** 前两个方法先生成后 AI 作为"基线"，后两个是 V2.0 迭代中追加的。AI 在追加方法时没有参照已有方法的模式。

**改进方案：** AI prompt 应附带同文件中的"参照方法"示例，或使用 project-level conventions.md 规范 Store 方法的行为模式。

### 3.3 UI 状态与 AI 流状态的耦合

ChatSessionPage 中，方案面板的显示/隐藏、流式生成动画、进度指示器等 UI 状态直接绑定到 chatStore/planStore 的响应式状态：

```vue
<!-- ChatSessionPage.vue 第 202 行 -->
<div v-if="chatStore.isStreaming" class="chat-session__streaming">...</div>

<!-- ChatSessionPage.vue 第 230 行 -->
<button v-if="!isDesktop && (planStore.isGenerating || planStore.currentPlan)">...</button>
```

**反思：** AI 使用了直观的响应式绑定，但当 AI 流状态复杂时（正在流式 + 进度更新 + 步骤切换），多个状态叠加可能导致竞态条件。例如：`isStreaming` 在 `done` 事件处理后才设为 false，但在处理过程中如果用户快速操作，可能会触发多个 `sendMessage()`。

解决方案是 AI 在 chatStore 中加了防重复检查：

```typescript
// chatStore.ts 第 412-415 行
if (isStreaming.value) {
  console.warn('[chatStore] Already streaming, message dropped:', content)
  return
}
```

这是一个值得肯定的防护机制。

### 3.4 SSE 协议处理的取舍（ChatMessage.vue）

[ChatMessage.vue](../frontend/src/components/chat/ChatMessage.vue) 第 13 行实例化了 `markdown-it` 并使用 `v-html` 渲染 Markdown：

```typescript
const md = new MarkdownIt({ html: false, breaks: true, linkify: true })
```

**安全反思：** AI 正确地将 `html: false` 设置，防止了 XSS 攻击。但在 ChatSessionPage 和其他组件中，AI 生成的 `v-html` 绑定需要谨慎审查。当前方案是安全的，但任何对 `html` 选项的修改都需要安全 review。

---

## 四、量化分析

### 4.1 AI 生成代码占比估算

| 模块 | 估算行数 | AI 生成比例 | AI 表现评级 |
|------|---------|------------|-----------|
| Store 层（7 个 Store） | ~1,200 行 | 90% | ★★★★☆ |
| API 封装层 | ~400 行 | 95% | ★★★★★ |
| TypeScript 类型定义 | ~500 行 | 80% | ★★★★★ |
| Vue 组件模板/样式 | ~3,000 行 | 60% | ★★★☆☆ |
| Vue 组件脚本逻辑 | ~1,500 行 | 75% | ★★★★☆ |
| 测试 mock 与用例 | ~400 行 | 90% | ★★★★☆ |
| 工具函数 | ~300 行 | 85% | ★★★★☆ |
| 路由配置 | ~100 行 | 50% | ★★★☆☆ |
| 样式/CSS | ~2,000 行 | 30% | ★★☆☆☆ |
| **总计** | **~9,400 行** | **约 70%** | |

### 4.2 问题密度

| 问题类型 | 发现数 | 修复周期 | 严重程度 |
|---------|-------|---------|---------|
| 代码重复（两套实现） | 3 处 | 人工 review 发现后清理 | 中等 |
| Store 方法行为不一致 | 2 处 | V2.0 迭代中修复 | 低 |
| 竞态条件隐患 | 1 处 | 已有防护机制 | 低 |
| 类型错误 | 4 处 | 编译阶段捕获 | 低 |
| SSE 事件处理遗漏（message_delta 静默） | 1 处 | 设计取舍，影响低 | 低 |

---

## 五、经验总结

### 5.1 前端 AI 辅助的最佳场景

1. **API 封装层 + 类型定义**：模板化程度最高，AI 零失误。前端 9 个 API 模块约 400 行代码几乎全部由 AI 生成，无需修改。

2. **Store 状态管理骨架**：CRUD 模式的 Store action（fetch/update/delete）AI 生成质量极高，但需要人工检查**方法行为一致性**（是否自动更新 state）。

3. **数据转换/归一化函数**：纯函数式的数据映射（如 `normalizeSSESummary()`）是 AI 的强项，输入输出明确，逻辑独立。

4. **测试 mock 数据生成**：AI 生成的 mock SSE 事件流可以构建完整的测试基础设施，让前端脱离后端独立开发。

5. **CSS 动画与 UI 细节**：AI 对流式加载动画（脉冲点、渐变条、面板滑入）的设计超出了预期——只是纯描述"朋友感"和"温暖"就产生了有情感的设计。

### 5.2 前端 AI 辅助的薄弱环节

1. **代码复用**：AI 不会自动发现已有工具类，容易生成重复功能。需要 prompt 中明确指定复用路径。

2. **CSS 全局一致性**：AI 在 scoped style 内工作良好，但在全局样式（如 ChatMessage.vue 第 319 行的全局 markdown 样式）的组织上缺乏系统性。

3. **V2.0 迭代时的方法一致性**：追加新功能时，AI 倾向于参照最近的 prompt 而非同一文件中的既有模式。

4. **跨 Store 的状态协调**：chatStore 和 planStore 在 SSE 流处理中有交叉引用（`handleSSEEvent` 中调用 `usePlanStore()`），AI 生成的这种模式虽然能工作，但引入了循环依赖风险。

### 5.3 对前端团队的建议

1. **建立前端编码规范文件**（`.agent/frontend-conventions.md`），明确约定：
   - Store action 的返回值规范（统一返回 `ApiResponse` 还是解包后的 `data`）
   - 工具函数的放置目录规则
   - 组件 Props/Emits 的命名规范
   - API 封装层与 Store 的分工边界

2. **AI prompt 中主动提供上下文**：在让 AI 生成新代码时，附上同目录/同文件的 2-3 个"参照方法"作为示例。

3. **模板化代码全部交给 AI**：API 封装、类型定义、Store 骨架等重复性工作应全部由 AI 生成，人工专注于：
   - 业务逻辑校验
   - 状态一致性检查
   - 竞态条件分析
   - UI/UX 细节调优

4. **使用 Vitest 验证 AI 代码**：对 AI 生成的 Store action 编写轻量级单元测试，重点验证：
   - 状态是否正确更新
   - 边界条件是否处理
   - 异常情况下 state 是否回滚

5. **代码清理窗口**：每 2-3 天安排一次 AI 辅助的代码清理 session，专门处理：
   - 删除被覆盖的遗留函数（如 `mapSSESummaryToPlan`）
   - 合并功能重叠的 util（如两个 `generatePlanMarkdown`）
   - 统一 Store 方法的行为模式

---

## 六、结语

作为前端开发负责人，我的总体体验是：**AI 将前端的"工程效率"提升到新的高度，但"架构一致性"的责任仍然在人的肩上。**

具体来说，AI 在以下三个维度带来了质的变化：

1. **SSE 流式交互**：从 fetch 调用到 ReadableStream 读取再到事件分发，AI 一次性生成了完整实现。这在传统开发中需要参考多个 MDN 页面 + 社区最佳实践，至少半天的工作量被压缩到分钟级。

2. **测试基础设施**：AI 构建的 SSE mock 工厂（`createSSEStream()`）和完整的 Agent 管线模拟数据，让前端可以**在后端 API 还没写好时就开始开发**。这彻底改变了前后端协作的节奏。

3. **UI 细节品质**：流式加载动画（弹跳点、渐变条、面板滑入）、Markdown 渲染的细致排版、渐进式的进度展示——这些"讲究的细节"在传统开发中往往因工期紧张而被牺牲，但 AI 在生成骨架代码时天然包含了这些细节。

但 AI 的弱点同样明显：**它会遗忘自己写过的代码**。同一个功能出现两个版本、同一个 Store 的方法行为不一致、util 类和 Store 内联函数并存——这些问题的根因都是 AI 缺乏"全局记忆"。解决方案不是期待 AI 改进（虽然未来会），而是在工程规范上做好防御：

> **人定规范，AI 守规范；人做 code review，AI 补重复代码。**

让 AI 在前端开发中发挥最大价值的关键，不是让 AI 一次生成更多代码，而是给 AI 更清晰的参照系——编码规范、Store 模式、组件架构。这些"框架性文件"越清晰，AI 的输出就越一致。
