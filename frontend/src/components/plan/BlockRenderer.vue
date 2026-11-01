<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import type { ContentBlock, ContentBlockDayCard, ContentBlockBudgetChart, ContentBlockMap, ContentBlockTrafficList, ContentBlockList } from '@/types/plan'
import DayCard from '@/components/plan/DayCard.vue'
import BudgetChart from '@/components/plan/BudgetChart.vue'
import MapContainer from '@/components/map/MapContainer.vue'

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

defineProps<{
  blocks: ContentBlock[]
  activeDay?: number
  compact?: boolean
}>()

defineEmits<{
  daySelect: [day: number]
}>()

function toDayCard(block: ContentBlock): ContentBlockDayCard {
  return block.data as unknown as ContentBlockDayCard
}

function toBudget(block: ContentBlock): { total: number; breakdown: Record<string, number> } {
  const b = block.data as unknown as ContentBlockBudgetChart
  return { total: b.total ?? 0, breakdown: b.breakdown ?? {} }
}

function toMap(block: ContentBlock): { markers: ContentBlockMap['markers']; polyline?: Array<[number, number][]> } {
  const d = block.data as unknown as ContentBlockMap
  return {
    markers: d.markers,
    polyline: d.route_path && d.route_path.length > 1 ? [d.route_path] : undefined,
  }
}

function toTrains(block: ContentBlock): ContentBlockTrafficList['trains'] {
  return (block.data as unknown as ContentBlockTrafficList).trains
}

const TRAIN_SEATS = [
  { name: '商务座', field: 'businessClass' },
  { name: '一等座', field: 'firstClass' },
  { name: '二等座', field: 'secondClass' },
  { name: '软卧', field: 'softSleeper' },
  { name: '硬卧', field: 'hardSleeper' },
  { name: '硬座', field: 'hardSeat' },
  { name: '无座', field: 'noSeat' },
]

function trainSeatRows(train: any) {
  const prices = train?.prices || {}
  const configuredSeats = new Set(TRAIN_SEATS.map(seat => seat.name))
  const rows = TRAIN_SEATS
    .filter(seat => Object.prototype.hasOwnProperty.call(prices, seat.name) || (train?.[seat.field] && train[seat.field] !== '--'))
    .map(seat => ({
      seat: seat.name,
      price: prices[seat.name],
      availability: train?.[seat.field] && train[seat.field] !== '--' ? String(train[seat.field]) : '余票未知',
    }))

  for (const [seat, price] of Object.entries(prices)) {
    if (!configuredSeats.has(seat)) rows.push({ seat, price, availability: '余票未知' })
  }
  return rows
}

function availabilityClass(availability: string): string {
  if (availability === '余票未知') return 'unknown'
  if (/无票|停售|候补/.test(availability)) return 'sold-out'
  return 'available'
}

function toList(block: ContentBlock): ContentBlockList {
  return block.data as unknown as ContentBlockList
}

const iconMap: Record<string, string> = {
  landmark: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
  warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  tip: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 008.91 14"/></svg>',
  info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
  food: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8h1a4 4 0 010 8h-1"/><path d="M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>',
  train: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3l-3 9h12l-3-9"/><path d="M9 21l3-9 3 9"/></svg>',
  sun: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
}
</script>

<template>
  <div
    class="block-renderer"
    :class="{ 'block-renderer--compact': compact }"
  >
    <template
      v-for="(block, i) in blocks"
      :key="i"
    >
      <!-- Header: 方案概览头部 -->
      <div
        v-if="block.type === 'header'"
        class="block-header"
      >
        <div class="block-header__badge">
          {{ (block.data as any).days || '' }}日行程
        </div>
        <h1 class="block-header__title">
          {{ (block.data as any).title || '方案详情' }}
        </h1>
        <div class="block-header__route">
          <span class="block-header__city">{{ (block.data as any).origin || '' }}</span>
          <span class="block-header__arrow">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="#E8A87C"
              stroke="none"
            ><path
              d="M5 12h14M13 5l7 7-7 7"
              stroke="#E8A87C"
              stroke-width="2"
              fill="none"
            /></svg>
          </span>
          <span class="block-header__city block-header__city--dest">{{ (block.data as any).destination || '' }}</span>
        </div>
        <div class="block-header__meta">
          <span class="block-header__tag">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            ><rect
              x="3"
              y="4"
              width="18"
              height="18"
              rx="2"
            /><line
              x1="16"
              y1="2"
              x2="16"
              y2="6"
            /><line
              x1="8"
              y1="2"
              x2="8"
              y2="6"
            /></svg>
            {{ (block.data as any).days || '' }}天
          </span>
          <span class="block-header__tag">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            ><circle
              cx="12"
              cy="12"
              r="10"
            /><path d="M12 6v6l4 2" /></svg>
            {{ (block.data as any).pace || '适中' }}节奏
          </span>
          <span class="block-header__tag">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            ><circle
              cx="12"
              cy="8"
              r="4"
            /><path d="M20 21a8 8 0 10-16 0" /></svg>
            {{ (block.data as any).traveler_count || 1 }}人
          </span>
        </div>
        <div class="block-header__cost-bar">
          <div class="block-header__cost-info">
            <span>总预算 <strong>&yen;{{ (block.data as any).total_budget ?? 0 }}</strong></span>
            <span>预估花费 <strong>&yen;{{ (block.data as any).estimated_cost ?? 0 }}</strong></span>
            <span
              class="block-header__remaining"
              :class="{ 'block-header__remaining--over': ((block.data as any).estimated_cost || 0) > ((block.data as any).total_budget || 0) }"
            >
              剩余 &yen;{{ Math.max(((block.data as any).total_budget || 0) - ((block.data as any).estimated_cost || 0), 0) }}
            </span>
          </div>
          <div class="block-header__bar-track">
            <div
              class="block-header__bar-fill"
              :style="{ width: Math.min((block.data as any).estimated_cost || 0) / ((block.data as any).total_budget || 1) * 100 + '%' }"
            />
          </div>
        </div>
      </div>

      <!-- Highlights: 行程亮点 -->
      <div
        v-else-if="block.type === 'highlights'"
        class="block-highlights"
      >
        <h3 class="block-section-title">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            style="vertical-align:middle;margin-right:6px"
          ><path d="M22 11.08V12a10 10 0 11-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
          行程亮点
        </h3>
        <div class="block-highlights__grid">
          <div
            v-for="(item, hi) in (block.data as any).items || []"
            :key="hi"
            class="block-highlights__card"
          >
            <div class="block-highlights__emoji">
              {{ item.emoji || '✨' }}
            </div>
            <div class="block-highlights__text">
              {{ item.text }}
            </div>
          </div>
        </div>
      </div>

      <!-- Section: 章节标题 -->
      <div
        v-else-if="block.type === 'section'"
        class="block-section"
      >
        <!-- eslint-disable vue/no-v-html -->
        <h2 class="block-section__title">
          <span
            class="block-section__icon"
            v-html="iconMap[(block.data as any).icon || 'info'] || ''"
          />
          {{ (block.data as any).title }}
        </h2>
        <!-- eslint-enable vue/no-v-html -->
        <p
          v-if="(block.data as any).subtitle"
          class="block-section__subtitle"
        >
          {{ (block.data as any).subtitle }}
        </p>
      </div>

      <!-- Text: Markdown 文本 -->
      <!-- eslint-disable vue/no-v-html -->
      <div
        v-else-if="block.type === 'text'"
        class="block-text"
        v-html="md.render((block.data as any).content || '')"
      />
      <!-- eslint-enable vue/no-v-html -->

      <!-- Divider -->
      <hr
        v-else-if="block.type === 'divider'"
        class="block-divider"
      >

      <!-- DayCard: 每日行程 -->
      <DayCard
        v-else-if="block.type === 'day_card'"
        :day="toDayCard(block)"
        :default-expanded="toDayCard(block).day === 1"
      />

      <!-- BudgetChart: 预算环形图 -->
      <div
        v-else-if="block.type === 'budget_chart'"
        class="block-budget-wrapper"
      >
        <h3 class="block-section-title">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            style="vertical-align:middle;margin-right:6px"
          ><circle
            cx="12"
            cy="12"
            r="10"
          /><path d="M12 6v6l4 2" /></svg>
          预算分布
        </h3>
        <BudgetChart :budget="toBudget(block)" />
      </div>

      <!-- Map: 高德地图 -->
      <div
        v-else-if="block.type === 'map'"
        class="block-map-wrapper"
      >
        <MapContainer
          :markers="toMap(block).markers || []"
          :polyline="toMap(block).polyline || []"
          :center="[112.98, 28.19]"
          :zoom="12"
        />
      </div>

      <!-- TrafficList: 车次列表 -->
      <div
        v-else-if="block.type === 'traffic_list'"
        class="block-traffic"
      >
        <table class="block-traffic__table">
          <thead>
            <tr>
              <th>车次</th>
              <th>出发</th>
              <th>到达</th>
              <th>历时</th>
              <th>票价 / 余票</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="t in toTrains(block)"
              :key="t.trainCode"
            >
              <td><strong class="block-traffic__code">{{ t.trainCode }}</strong></td>
              <td><span class="block-traffic__station">{{ t.fromStationName }}</span><span class="block-traffic__time">{{ t.departureTime }}</span></td>
              <td><span class="block-traffic__station">{{ t.toStationName }}</span><span class="block-traffic__time">{{ t.arrivalTime }}</span></td>
              <td><span class="block-traffic__duration">{{ t.duration }}</span></td>
              <td>
                <div
                  v-for="row in trainSeatRows(t)"
                  :key="row.seat"
                  class="block-traffic__seat-row"
                >
                  <span class="block-traffic__seat-name">{{ row.seat }}</span>
                  <span class="block-traffic__seat-price">{{ row.price !== undefined && row.price !== '' ? `¥${row.price}` : '价格未知' }}</span>
                  <span
                    class="block-traffic__availability"
                    :class="`block-traffic__availability--${availabilityClass(row.availability)}`"
                  >{{ row.availability }}</span>
                </div>
                <span
                  v-if="!trainSeatRows(t).length"
                  class="block-traffic__empty-seat"
                >暂无席别信息</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Callout: 提示卡片 -->
      <div
        v-else-if="block.type === 'callout'"
        class="block-callout"
        :class="`block-callout--${(block.data as any).level || 'info'}`"
      >
        <!-- eslint-disable vue/no-v-html -->
        <div
          class="block-callout__icon"
          v-html="iconMap[(block.data as any).icon || 'info'] || iconMap.info"
        />
        <!-- eslint-enable vue/no-v-html -->
        <div class="block-callout__body">
          <div class="block-callout__level-tag">
            {{ (block.data as any).level === 'warning' ? '提醒' : (block.data as any).level === 'success' ? '建议' : '提示' }}
          </div>
          <div
            v-if="(block.data as any).title"
            class="block-callout__title"
          >
            {{ (block.data as any).title }}
          </div>
          <div class="block-callout__text">
            {{ (block.data as any).text || '' }}
          </div>
        </div>
      </div>

      <!-- List: 标签列表 -->
      <div
        v-else-if="block.type === 'list'"
        class="block-list-wrapper"
      >
        <h3
          v-if="(block.data as any).title"
          class="block-section-title"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            style="vertical-align:middle;margin-right:6px"
          ><line
            x1="8"
            y1="6"
            x2="21"
            y2="6"
          /><line
            x1="8"
            y1="12"
            x2="21"
            y2="12"
          /><line
            x1="8"
            y1="18"
            x2="21"
            y2="18"
          /><line
            x1="3"
            y1="6"
            x2="3.01"
            y2="6"
          /><line
            x1="3"
            y1="12"
            x2="3.01"
            y2="12"
          /><line
            x1="3"
            y1="18"
            x2="3.01"
            y2="18"
          /></svg>
          {{ (block.data as any).title }}
        </h3>
        <div
          v-if="(block.data as any).description"
          class="block-list__desc"
        >
          {{ (block.data as any).description }}
        </div>
        <div
          v-if="toList(block).items?.length"
          class="block-list"
        >
          <span
            v-for="item in toList(block).items"
            :key="item"
            class="block-list__tag"
          >{{ item }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.block-renderer { width: 100%; }
.block-renderer--compact { font-size: 13px; }

/* ---- Section Title ---- */
.block-section-title {
  font-size: 15px; font-weight: 600; margin: 20px 0 10px;
  color: var(--color-text-primary); display: flex; align-items: center;
}
.block-section {
  margin: 24px 0 12px;
}
.block-section__title {
  font-size: 17px; font-weight: 600; margin: 0 0 4px; color: var(--color-text-primary);
  display: flex; align-items: center; gap: 8px;
}
.block-section__icon {
  display: inline-flex; align-items: center; color: var(--color-brand-500);
  width: 20px; height: 20px;
}
.block-section__subtitle {
  font-size: 13px; color: var(--color-text-tertiary); margin: 0; line-height: 1.5;
}

/* ---- Header ---- */
.block-header {
  padding: 20px 0 16px;
}
.block-header__badge {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 500; color: white; background: var(--color-brand-500);
  margin-bottom: 10px;
}
.block-header__title {
  font-size: 24px; font-weight: 700; margin: 0 0 8px;
  color: var(--color-text-primary); line-height: 1.3;
}
.block-header__route {
  display: flex; align-items: center; gap: 4px; margin-bottom: 10px;
}
.block-header__arrow { display: flex; align-items: center; }
.block-header__city {
  font-size: 16px; font-weight: 500; color: var(--color-text-secondary);
}
.block-header__city--dest { color: var(--color-brand-600); font-weight: 700; font-size: 18px; }
.block-header__meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.block-header__tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 10px; border-radius: 6px; background: var(--color-bg-secondary);
  font-size: 12px; color: var(--color-text-secondary);
}
.block-header__tag svg { width: 13px; height: 13px; color: var(--color-brand-400); }
.block-header__cost-bar {
  background: var(--color-bg-card); border: 1px solid var(--color-border-light);
  border-radius: 8px; padding: 12px 16px;
}
.block-header__cost-info {
  display: flex; justify-content: space-between; font-size: 12px; color: var(--color-text-secondary); margin-bottom: 8px;
}
.block-header__cost-info strong { color: var(--color-text-primary); font-weight: 600; }
.block-header__remaining--over { color: var(--color-red-600); }
.block-header__bar-track {
  height: 6px; background: var(--color-bg-secondary); border-radius: 3px; overflow: hidden;
}
.block-header__bar-fill {
  height: 100%; background: linear-gradient(90deg, #E8A87C, #D49366);
  border-radius: 3px; transition: width 0.5s ease;
}

/* ---- Highlights ---- */
.block-highlights {
  margin: 16px 0;
}
.block-highlights__grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px;
}
.block-highlights__card {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px; border-radius: 10px; background: var(--color-brand-50);
  border: 1px solid var(--color-brand-100);
}
.block-highlights__emoji { font-size: 20px; flex-shrink: 0; }
.block-highlights__text { font-size: 13px; line-height: 1.5; color: var(--color-text-secondary); }

/* ---- Text ---- */
.block-text {
  font-size: 14px; line-height: 1.7; color: var(--color-text-primary); margin: 16px 0;
}
.block-text :deep(h2) { font-size: 16px; font-weight: 600; margin: 20px 0 8px; color: var(--color-brand-700); }
.block-text :deep(h3) { font-size: 14px; font-weight: 600; margin: 14px 0 6px; }
.block-text :deep(blockquote) {
  margin: 10px 0; padding: 8px 14px;
  border-left: 3px solid var(--color-brand-300); background: var(--color-brand-50);
  border-radius: 0 8px 8px 0; color: var(--color-text-secondary); font-size: 13px;
}
.block-text :deep(table) { width: auto; border-collapse: collapse; font-size: 13px; margin: 10px 0; }
.block-text :deep(th), .block-text :deep(td) { border: 1px solid var(--color-border); padding: 6px 10px; text-align: left; }
.block-text :deep(th) { background: var(--color-brand-50); font-weight: 500; color: var(--color-brand-700); }
/* 预算表格的数字列右对齐 */
.block-text :deep(td:nth-child(2)),
.block-text :deep(td:nth-child(3)) { text-align: right; font-variant-numeric: tabular-nums; }
/* 超支行红色标记 */
.block-text :deep(td:last-child) { white-space: nowrap; }
.block-text :deep(ul), .block-text :deep(ol) { padding-left: 20px; margin: 6px 0; }
.block-text :deep(li) { margin-bottom: 4px; line-height: 1.6; }
.block-text :deep(hr) { border: none; border-top: 1px solid var(--color-border-light); margin: 20px 0; }
.block-text :deep(p) { margin: 0 0 8px; }
.block-text :deep(p:last-child) { margin-bottom: 0; }

.block-divider { border: none; border-top: 1px solid var(--color-border-light); margin: 24px 0; }

/* ---- Budget wrapper ---- */
.block-budget-wrapper { margin: 16px 0; }

/* ---- Map ---- */
.block-map-wrapper { height: 360px; margin: 16px 0; border-radius: 10px; overflow: hidden; border: 1px solid var(--color-border-light); }

/* ---- Traffic ---- */
.block-traffic { margin: 16px 0; }
.block-traffic__hint { font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 8px; }
.block-traffic__table { width: 100%; border-collapse: collapse; font-size: 13px; border-radius: 8px; overflow: hidden; border: 1px solid var(--color-border-light); }
.block-traffic__table th {
  background: var(--color-brand-50); font-weight: 500; color: var(--color-brand-700);
  padding: 8px 12px; text-align: left; border-bottom: 2px solid var(--color-brand-200);
  font-size: 12px;
}
.block-traffic__table td { padding: 8px 12px; border-bottom: 1px solid var(--color-border-light); vertical-align: middle; }
.block-traffic__code { font-weight: 600; color: var(--color-brand-600); font-size: 13px; }
.block-traffic__station { display: block; font-weight: 500; color: var(--color-text-primary); }
.block-traffic__time { display: block; font-size: 12px; color: var(--color-text-tertiary); }
.block-traffic__duration { padding: 2px 8px; background: var(--color-bg-secondary); border-radius: 4px; font-size: 12px; white-space: nowrap; }
.block-traffic__seat-row { display: grid; grid-template-columns: 52px 62px auto; align-items: center; gap: 6px; white-space: nowrap; font-size: 12px; line-height: 1.8; }
.block-traffic__seat-name { color: var(--color-text-secondary); }
.block-traffic__seat-price { color: var(--color-text-primary); font-variant-numeric: tabular-nums; }
.block-traffic__availability { justify-self: start; padding: 0 6px; border-radius: 999px; font-size: 11px; line-height: 18px; }
.block-traffic__availability--available { color: var(--color-success); background: color-mix(in srgb, var(--color-success) 12%, transparent); }
.block-traffic__availability--sold-out { color: var(--color-error); background: color-mix(in srgb, var(--color-error) 10%, transparent); }
.block-traffic__availability--unknown { color: var(--color-text-tertiary); background: var(--color-bg-secondary); }
.block-traffic__empty-seat { font-size: 12px; color: var(--color-text-tertiary); }

/* ---- Callout ---- */
.block-callout {
  display: flex; gap: 12px; padding: 14px 18px; border-radius: 10px; margin: 14px 0;
  border-left: 4px solid;
}
.block-callout--info { background: var(--color-brand-50); border-color: var(--color-brand-300); }
.block-callout--warning { background: var(--color-brand-50); border-color: var(--color-warning); }
.block-callout--success { background: var(--color-brand-50); border-color: var(--color-success); }
.block-callout__icon { font-size: 20px; line-height: 1.4; flex-shrink: 0; color: var(--color-brand-500); width: 20px; height: 20px; }
.block-callout--warning .block-callout__icon { color: var(--color-warning); }
.block-callout--success .block-callout__icon { color: var(--color-success); }
.block-callout__level-tag {
  font-size: 11px; font-weight: 500; display: inline-block; padding: 1px 8px;
  border-radius: 4px; margin-bottom: 4px;
  background: var(--color-brand-100); color: var(--color-brand-700);
}
.block-callout--warning .block-callout__level-tag { background: var(--color-warning); opacity: 0.85; color: #fff; }
.block-callout--success .block-callout__level-tag { background: var(--color-success); opacity: 0.85; color: #fff; }
.block-callout__title { font-weight: 600; font-size: 14px; margin-bottom: 2px; color: var(--color-text-primary); }
.block-callout__text { font-size: 13px; line-height: 1.5; color: var(--color-text-secondary); }

/* ---- List ---- */
.block-list-wrapper { margin: 16px 0; }
.block-list__desc { font-size: 13px; color: var(--color-text-tertiary); margin-bottom: 8px; line-height: 1.5; }
.block-list { display: flex; flex-wrap: wrap; gap: 6px; }
.block-list__tag {
  display: inline-block; padding: 4px 12px; border-radius: 999px;
  font-size: 12px; background: var(--color-brand-50); color: var(--color-brand-700);
  border: 1px solid var(--color-brand-100);
}
</style>
