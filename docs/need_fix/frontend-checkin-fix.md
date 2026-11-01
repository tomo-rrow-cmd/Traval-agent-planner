# 前端签到功能修复方案

> 基于 2026-07-14 代码审查，按修复优先级排序

---

## 🔴 P0 — 功能缺失 / 未使用代码

### F1. `CheckInButton.vue` 已创建但未被使用

**现象**：`frontend/src/components/trip/CheckInButton.vue` 是一个独立的签到按钮组件（含签到动画、位置验证接口），但没有任何地方 import 它。

**当前使用点**：`TripTimeline.vue:66-71` 使用的是**内联原生 `<button>`**，没有用此组件。

**修复方案（选其一）**：

**方案 A（推荐）**：在 `TripTimeline.vue` 中替换为 `CheckInButton` 组件

```vue
<!-- TripTimeline.vue -->
<script setup>
import CheckInButton from './CheckInButton.vue'
</script>

<template>
  <!-- 替换 line 66-71 的内联按钮 -->
  <CheckInButton
    v-else
    :poi-type="slot.type"
    :poi-name="slot.name"
    @checkin="({ type, name }) => emit('checkin', type, name)"
  />
</template>
```

**方案 B**：如果确认不需要独立组件，删除 `CheckInButton.vue`。

**涉及文件**：
- [frontend/src/components/trip/CheckInButton.vue](frontend/src/components/trip/CheckInButton.vue)
- [frontend/src/components/trip/TripTimeline.vue](frontend/src/components/trip/TripTimeline.vue)

---

### F2. `todayCheckins` computed 始终返回全部签到

**现象**：`TripExecutePage.vue` 未使用此 computed（目前只用 `store.checkins`），但作为 store 的公共 getter，逻辑错误会影响将来的使用。

**根因**（[frontend/src/store/tripStore.ts:30-37](frontend/src/store/tripStore.ts#L30-L37)）：

```typescript
const todayCheckins = computed(() => {
  if (!activeTrip.value) return []
  return checkins.value.filter(c => {
    return true  // ❌ 没有实际过滤逻辑
  })
})
```

**修复**：后端修复 B1（`source_day` 列）后，前端利用 `source_day` 字段过滤：

```typescript
const todayCheckins = computed(() => {
  const trip = activeTrip.value
  if (!trip) return []
  const today = trip.current_day
  // 优先用 source_day，回落用 actual_at 日期推断
  return checkins.value.filter(c => {
    if (c.source_day !== undefined) return c.source_day === today
    if (c.actual_at) {
      const d = new Date(c.actual_at)
      return d.getDate() === new Date().getDate()
    }
    return false
  })
})
```

同时需要在 `CheckinRecord` 类型中补充 `source_day`：

```typescript
// frontend/src/api/trip.ts — CheckinRecord 接口
export interface CheckinRecord {
  // ...现有字段
  source_day?: number  // 新增
}
```

**涉及文件**：
- [frontend/src/store/tripStore.ts](frontend/src/store/tripStore.ts)
- [frontend/src/api/trip.ts](frontend/src/api/trip.ts)

---

## 🟡 P1 — 功能缺陷

### F3. `poi_type` 前后端不一致（前端用 `food`，后端用 `restaurant`）

**现象**：在《方案详情》中活动类型为 `'food'`（[frontend/src/types/plan.ts:14](frontend/src/types/plan.ts#L14)），但后端签到 API 期望 `poi_type` 为 `'restaurant'`（[app/schemas/trip.py:52](app/schemas/trip.py#L52)）。`TripTimeline.vue:43` 又映射了 `'food' || 'restaurant'`。

**影响**：
- `TripExecutePage.vue:44` 从 `DailyItinerary.activities` 提取 `type` 时拿到的 `'food'` 直接传给签到 API
- 后端只认 `'restaurant'`，类型不匹配不会影响 DB 存储（字符串列），但日志和后续处理可能不准

**修复**：在 `TripExecutePage.vue` 的 `planSlots` 计算中做类型映射：

```typescript
// TripExecutePage.vue — planSlots 中 type 映射
const TYPE_MAP: Record<string, string> = {
  food: 'restaurant',
  attraction: 'attraction',
  shopping: 'other',
  rest: 'other',
  entertainment: 'other',
  accommodation: 'hotel',
  transport: 'other',
}

// 在构建 slots 时
slots.push({
  time: act.time_slot || '09:00',
  type: TYPE_MAP[act.type] || act.type,
  name: act.title,
})
```

同时统一 `TripTimeline.vue` 的类型显示逻辑：

```typescript
function getIcon(type: string): string {
  const normalized = type === 'food' ? 'restaurant' : type
  return normalized === 'attraction' ? '🏯' :
         normalized === 'restaurant' ? '🍜' :
         normalized === 'hotel' ? '🏨' : '📍'
}
```

**涉及文件**：
- [frontend/src/views/TripExecutePage.vue](frontend/src/views/TripExecutePage.vue)
- [frontend/src/components/trip/TripTimeline.vue](frontend/src/components/trip/TripTimeline.vue)

---

### F4. `planSlots` 只提取 `activities` 和 `meals`，遗漏住宿/交通等 POI

**现象**：时间线只显示景点和餐厅，缺少酒店入住、交通接送等重要节点。

**根因**（[frontend/src/views/TripExecutePage.vue:40-53](frontend/src/views/TripExecutePage.vue#L40-L53)）：

```typescript
// 只处理了 activities 和 meals
for (const act of day.activities || []) { ... }
if ((day as any).meals?.length) { ... }
```

**修复**：加入 `accommodation` 和 `transport` 节点：

```typescript
const planSlots = computed(() => {
  const plan = planStore.currentPlan
  const day = plan?.daily_itinerary?.find(d => d.day === (store.activeTrip?.current_day ?? 1))
  if (!day) return []
  const slots: Array<{ time: string; type: string; name: string }> = []

  // 1. 加入入住/退房节点
  if (day.accommodation) {
    slots.push({
      time: day.accommodation.check_in || '14:00',
      type: 'hotel',
      name: `入住 ${day.accommodation.hotel_name}`,
    })
  }

  // 2. 活动节点
  for (const act of day.activities || []) {
    slots.push({
      time: act.time_slot || '09:00',
      type: TYPE_MAP[act.type] || act.type,
      name: act.title,
    })
  }

  // 3. 用餐节点（从 day.meals 或 daily_itinerary meallist 等）
  const meals = (day as any).meals ?? []
  for (const m of meals) {
    slots.push({
      time: m.time || '12:00',
      type: 'restaurant',
      name: m.restaurant || '用餐',
    })
  }

  // 4. 按时间排序
  slots.sort((a, b) => a.time.localeCompare(b.time))

  return slots
})
```

**涉及文件**：
- [frontend/src/views/TripExecutePage.vue](frontend/src/views/TripExecutePage.vue)

---

### F5. `getSlotStatus` 匹配逻辑过于简单

**现象**：`TripTimeline.vue:30-34` 仅靠 `poi_name` 精确匹配来判定是否已签到。如果用户签到时的 `poi_name` 与方案中的 `title` 有细微差异（例如"西湖风景区" vs "西湖"），已签到状态无法正确显示。

**修复**：增加模糊匹配和 `poi_type` 联合判断：

```typescript
function getSlotStatus(name: string, type: string): 'done' | 'pending' {
  return props.checkins.some(c => {
    // 1. 精确匹配
    if (c.poi_name === name) return true
    // 2. 包含匹配（签到名包含在 slot 名中，或反之）
    if (c.poi_name && name && (c.poi_name.includes(name) || name.includes(c.poi_name))) {
      return c.poi_type === type || normalizeType(c.poi_type) === normalizeType(type)
    }
    return false
  }) ? 'done' : 'pending'
}

function normalizeType(t: string): string {
  return t === 'food' ? 'restaurant' : t
}
```

**涉及文件**：
- [frontend/src/components/trip/TripTimeline.vue](frontend/src/components/trip/TripTimeline.vue)

---

### F6. 签到弹窗未发送 `actual_at` 时间戳

**现象**：`TripExecutePage.vue:79-85` 的 `handleCheckinSubmit` 未设置 `actual_at`，后端 DB 中 `actual_at` 为空，`time_delta_min` 无法计算。

**修复**：

```typescript
async function handleCheckinSubmit() {
  if (!checkinTarget.value) return
  try {
    await store.doCheckin({
      poi_type: checkinTarget.value.type,
      poi_name: checkinTarget.value.name,
      actual_at: new Date().toISOString(),  // ✅ 补充当前时间
      rating: checkinRating.value || undefined,
      note: checkinNote.value || undefined,
      actual_cost: checkinCost.value || undefined,
    })
    // ...
  }
}
```

**涉及文件**：
- [frontend/src/views/TripExecutePage.vue](frontend/src/views/TripExecutePage.vue)

---

### F7. 签到后时间线未重新定位到当日

**现象**：签到成功后虽刷新了签到列表，但 `TripTimeline` 没有滚动到最新签到项的可视反馈。

**修复**（可选）：在 `TripTimeline` 中监听 `checkins` 变化，高亮最后签到的项：

```vue
<!-- TripTimeline.vue -->
<script setup>
import { ref, watch, nextTick } from 'vue'

const lastSignedName = ref('')

watch(() => props.checkins.length, async () => {
  if (props.checkins.length > 0) {
    lastSignedName.value = props.checkins[0].poi_name
    await nextTick()
    // 可选：滚动到对应元素
  }
})
</script>
```

**涉及文件**：
- [frontend/src/components/trip/TripTimeline.vue](frontend/src/components/trip/TripTimeline.vue)

---

## 🔵 P2 — 体验优化

### F8. 签到弹窗缺少 loading 状态

**现象**：点击"确认签到"后没有禁用按钮 / loading 反馈，如果网络慢可能造成重复提交。

**修复**：

```vue
<script setup>
const isSubmitting = ref(false)

async function handleCheckinSubmit() {
  if (isSubmitting.value || !checkinTarget.value) return
  isSubmitting.value = true
  try {
    await store.doCheckin({ ... })
    showCheckinForm.value = false
  } catch {
    // 错误处理
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
    {{ isSubmitting ? '签到中...' : '确认签到 ✓' }}
  </button>
</template>
```

**涉及文件**：
- [frontend/src/views/TripExecutePage.vue](frontend/src/views/TripExecutePage.vue)

### F9. 缺少地理位置校验接口对接

**现象**：`CheckInButton` 组件声明了 `disabled` prop 用于位置验证，但没有任何 GPS 距离计算逻辑。用户可以在任意位置签到，无法确认是否真的到达。

**修复**（V2.1 范围，本次可预留接口）：

```typescript
// TripExecutePage.vue — 签到前校验
import { useGeolocation } from '@/composables/useGeolocation'

async function openCheckin(type: string, name: string, poiLocation?: { lat: number; lng: number }) {
  // 如果 POI 有坐标，校验距离
  if (poiLocation) {
    const { lat, lng } = await useGeolocation().getCurrentPosition()
    const distance = calcDistance(lat, lng, poiLocation.lat, poiLocation.lng)
    if (distance > 500) {  // 超过 500 米提醒
      if (!confirm(`您当前距离签到点约 ${distance}m，确认签到吗？`)) return
    }
  }
  checkinTarget.value = { type, name }
  resetCheckinForm()
  showCheckinForm.value = true
}
```

**涉及文件**：
- [frontend/src/components/trip/CheckInButton.vue](frontend/src/components/trip/CheckInButton.vue)
- [frontend/src/views/TripExecutePage.vue](frontend/src/views/TripExecutePage.vue)

---

## 📋 修改清单

| ID | 文件 | 变更类型 | 优先级 |
|---|---|---|---|
| F1 | `TripTimeline.vue` | 导入并使用 `CheckInButton` | P0 🔴 |
| F1 | `CheckInButton.vue` | 可选：删除（如果不用） | P0 🔴 |
| F2 | `tripStore.ts` | 修复 `todayCheckins` 过滤逻辑 | P0 🔴 |
| F2 | `api/trip.ts` | `CheckinRecord` +`source_day` | P0 🔴 |
| F3 | `TripExecutePage.vue` | 加类型映射表 | P1 🟡 |
| F3 | `TripTimeline.vue` | 统一 `getIcon` 类型 | P1 🟡 |
| F4 | `TripExecutePage.vue` | 扩展 `planSlots` 提取范围 | P1 🟡 |
| F5 | `TripTimeline.vue` | 模糊匹配 + 联合判定 | P1 🟡 |
| F6 | `TripExecutePage.vue` | 补传 `actual_at` | P1 🟡 |
| F7 | `TripTimeline.vue` | 签到后高亮最新项 | P2 🔵 |
| F8 | `TripExecutePage.vue` | 加 loading 防重复 | P2 🔵 |
| F9 | `CheckInButton.vue` / `TripExecutePage.vue` | 地理校验接口（预留） | P2 🔵 |
