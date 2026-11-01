<script setup lang="ts">
/* ============================================================
   DayCard — 单日行程卡片（父组件受控展开/折叠 + 内嵌小地图）
   标签状态由父组件的 expandedDays 控制
   点击卡片头部可切换展开/折叠，同时通知父组件更新标签状态
   ============================================================ */

import { ref, computed, watch } from 'vue'
import type { DailyItinerary } from '@/types/plan'
import { usePlanStore } from '@/store/planStore'
import IconTravel from "@/components/icons/IconTravel.vue"
import ActivityItem from './ActivityItem.vue'
import MapContainer from '@/components/map/MapContainer.vue'
import { cleanDisplayText } from './textFormat'
import { buildDailyMapData, type PlanMapMarker } from '@/utils/planMap'

export interface TrafficRouteStep {
  type: string
  line_name?: string
  line_full?: string
  departure_stop?: string
  arrival_stop?: string
  via_stops?: number
  distance?: number
  duration?: number
  direction?: string
}

export interface TrafficRoutePlan {
  cost?: number
  duration?: number
  walking_distance?: number
  distance?: number
  segments?: TrafficRouteStep[]
  night_bus?: boolean
}

/** 单段交通信息 */
export interface TrafficSegment {
  from: string
  to: string
  mode: string
  distance_km?: number
  time_min: number
  cost: number
  route_type?: string
  detail?: string
  plans?: TrafficRoutePlan[]
}

const props = withDefaults(defineProps<{
  day: DailyItinerary
  expanded?: boolean
  /** 该日所有 POI 标记（含酒店） */
  markers?: PlanMapMarker[]
  /** 该日完整路线：酒店 → 景点 → 餐饮 → ... → 酒店 */
  routePath?: Array<[number, number]>
  /** 该日交通明细（每段路线） */
  traffic?: TrafficSegment[]
}>(), {
  expanded: false,
  markers: () => [],
  routePath: () => [],
  traffic: () => [],
})

const emit = defineEmits<{
  toggle: [day: number]
  replaceActivity: [day: number, activityIndex: number]
  removeActivity: [day: number, activityIndex: number]
}>()

/** 内部展开状态：当 expanded prop 为 undefined 时使用 */
const internalExpanded = ref(props.expanded)
const expandedTrafficRows = ref<Set<number>>(new Set())
watch(() => props.expanded, (val) => {
  internalExpanded.value = val
})
const isExpanded = computed(() => {
  // 如果 props 中显式传了 expanded（非 undefined），使用 prop
  // 否则使用内部状态（兼容 BlockRenderer 场景）
  return props.expanded !== undefined ? props.expanded : internalExpanded.value
})

/** 交通方式图标映射 */
const MODE_ICON: Record<string, string> = {
  '地铁': '🚇', 'subway': '🚇',
  '公交': '🚌', 'bus': '🚌',
  '打车': '🚕', 'taxi': '🚕', 'driving': '🚗',
  '步行': '🚶', 'walking': '🚶',
  '骑行': '🚲', 'bike': '🚲',
  '高铁': '🚄', 'train': '🚄',
}

function modeIcon(mode: string): string {
  const normalized = normalizedMode(mode)
  return MODE_ICON[normalized] || MODE_ICON[mode] || '🚗'
}

function normalizedMode(mode: string): string {
  const value = String(mode || '').replace(/\(est\)/gi, '').trim()
  const key = value.toLowerCase()
  const labels: Record<string, string> = {
    transit: '公共交通',
    subway: '地铁',
    bus: '公交',
    driving: '打车',
    taxi: '打车',
    walking: '步行',
    bike: '骑行',
  }
  return labels[key] || value || '交通'
}

function isEstimatedTraffic(segment: TrafficSegment): boolean {
  return /\(est\)|估算/i.test(String(segment.mode || ''))
}

function trafficModeLabel(segment: TrafficSegment): string {
  const label = normalizedMode(segment.mode)
  return isEstimatedTraffic(segment) ? `${label}（估算）` : label
}

function toggleTrafficRow(index: number) {
  const next = new Set(expandedTrafficRows.value)
  if (next.has(index)) next.delete(index)
  else next.add(index)
  expandedTrafficRows.value = next
}

function isTrafficRowExpanded(index: number): boolean {
  return expandedTrafficRows.value.has(index)
}

function routePlans(segment: TrafficSegment): TrafficRoutePlan[] {
  return Array.isArray(segment.plans) ? segment.plans.slice(0, 3) : []
}

function planLabel(index: number): string {
  return index === 0 ? '推荐方案' : `备选方案 ${index}`
}

function formatMeters(value?: number): string {
  const meters = Number(value) || 0
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)}km`
  return `${Math.round(meters)}m`
}

function formatSeconds(value?: number): string {
  const seconds = Number(value) || 0
  return `${Math.max(1, Math.ceil(seconds / 60))}min`
}

function stepIcon(step: TrafficRouteStep): string {
  const type = String(step.type || '').toUpperCase()
  if (type === 'WALKING') return '🚶'
  if (type === 'SUBWAY') return '🚇'
  if (type === 'BUS') return '🚌'
  return '🚏'
}

function stepTitle(step: TrafficRouteStep): string {
  const type = String(step.type || '').toUpperCase()
  if (type === 'WALKING') return `步行 ${formatMeters(step.distance)}`
  return cleanDisplayText(step.line_name || step.line_full || (type === 'SUBWAY' ? '地铁' : '公交'))
}

function stepRoute(step: TrafficRouteStep): string {
  const departure = cleanDisplayText(step.departure_stop)
  const arrival = cleanDisplayText(step.arrival_stop)
  if (!departure && !arrival) return ''
  return `${departure || '上车站待确认'} → ${arrival || '下车站待确认'}`
}

function stepMeta(step: TrafficRouteStep): string {
  const parts: string[] = []
  if (step.via_stops) parts.push(`${step.via_stops}站`)
  if (step.duration) parts.push(formatSeconds(step.duration))
  if (step.direction) parts.push(`开往${cleanDisplayText(step.direction)}`)
  return parts.join(' · ')
}

/** 交通总时间和总费用 */
const trafficTotal = computed(() => {
  const segs = props.traffic || []
  return {
    time: segs.reduce((sum, segment) => sum + (Number(segment.time_min) || 0), 0),
    cost: segs.reduce((sum, segment) => sum + (Number(segment.cost) || 0), 0),
  }
})

/** 当天总花费：优先使用后端汇总，缺失时累加页面上展示的各类费用 */
const dayTotalCost = computed(() => {
  const day = props.day as any
  const declaredCost = Number(day.day_cost) || 0
  if (declaredCost > 0) return declaredCost

  const activityCost = (day.activities || []).reduce(
    (sum: number, activity: any) => sum + (Number(activity.cost ?? activity.price) || 0),
    0,
  )
  const mealCost = (day.meals || []).reduce(
    (sum: number, meal: any) => sum + (Number(meal.avg_price ?? meal.cost ?? meal.price) || 0),
    0,
  )
  const accommodationCost = Number(day.accommodation?.price ?? day.accommodation?.price_per_night) || 0

  return activityCost + mealCost + accommodationCost + trafficTotal.value.cost
})

const planStore = usePlanStore()
const fallbackMapData = computed(() => {
  const plan = planStore.currentPlan as any
  const hotelPlan = plan?.hotel_plan || {}
  const selectedHotel = hotelPlan.selected_hotel
    || (hotelPlan.recommendations || [])[0]
  return buildDailyMapData(props.day as any, selectedHotel || null)
})
const mapMarkers = computed(() => props.markers.length > 0
  ? props.markers
  : fallbackMapData.value.markers)
const mapRoutePath = computed(() => props.routePath.length > 0
  ? props.routePath
  : fallbackMapData.value.routePath)

function handleToggle() {
  emit('toggle', props.day.day)
}

function handleReplace(day: number, index: number) {
  emit('replaceActivity', day, index)
}

function handleRemove(day: number, index: number) {
  emit('removeActivity', day, index)
}
</script>

<template>
  <div
    class="day-card"
    :class="{ 'day-card--expanded': isExpanded }"
  >
    <div
      class="day-card__header"
      @click="handleToggle"
    >
      <div class="day-card__day-info">
        <span class="day-card__day-label">Day {{ day.day }}</span>
        <div class="day-card__date-info">
          <span class="day-card__date">{{ day.date }}</span>
          <span class="day-card__date-label">{{ day.date_label }}</span>
        </div>
      </div>
      <div class="day-card__summary-info">
        <span
          v-if="day.weather_summary"
          class="day-card__weather"
        >{{ day.weather_summary }}</span>
        <span class="day-card__day-cost">¥{{ dayTotalCost }}</span>
      </div>
      <div class="day-card__toggle">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          :style="{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="day-card__body"
      >
        <div class="day-card__timeline">
          <ActivityItem
            v-for="(act, idx) in day.activities"
            :key="idx"
            :activity="act"
            @replace="handleReplace(day.day, idx)"
            @remove="handleRemove(day.day, idx)"
          />
        </div>

        <!-- 餐饮 -->
        <div
          v-if="(day as any).meals?.length"
          class="day-card__meals"
        >
          <div class="day-card__section-label">
            🍽 餐饮
          </div>
          <div
            v-for="(m, i) in (day as any).meals"
            :key="'m'+i"
            class="meal-item"
          >
            <IconTravel
              name="sparkle"
              :size="16"
              class="meal-item__icon"
            />
            <div class="meal-item__info">
              <span class="meal-item__restaurant">{{ m.restaurant }}</span>
              <span class="meal-item__dish">{{ m.meal }}</span>
            </div>
            <div class="meal-item__right">
              <span
                v-if="m.avg_price"
                class="meal-item__price"
              >¥{{ m.avg_price }}</span>
              <p
                v-if="m.reason"
                class="meal-item__reason"
              >
                {{ m.reason }}
              </p>
            </div>
          </div>
        </div>

        <!-- 住宿信息 -->
        <div
          v-if="day.accommodation"
          class="day-card__accommodation"
        >
          <div class="accommodation-card">
            <IconTravel
              name="pin"
              :size="20"
              class="accommodation-card__icon"
            />
            <div class="accommodation-card__info">
              <div class="accommodation-card__name">
                {{ cleanDisplayText(day.accommodation.hotel_name) }}
              </div>
              <div class="accommodation-card__address">
                {{ cleanDisplayText(day.accommodation.address) }}
              </div>
            </div>
            <div class="accommodation-card__right">
              <div
                v-if="day.accommodation.rating"
                class="accommodation-card__rating"
              >
                ★ {{ day.accommodation.rating }}
              </div>
              <div class="accommodation-card__price">
                ¥{{ day.accommodation.price }}
              </div>
            </div>
          </div>
        </div>

        <!-- 交通明细 -->
        <div
          v-if="props.traffic?.length"
          class="day-card__traffic"
        >
          <div class="day-card__section-label">
            🚖 交通明细
          </div>
          <div class="traffic-table">
            <div
              v-for="(seg, i) in props.traffic"
              :key="i"
              class="traffic-row"
              :class="{ 'traffic-row--expanded': isTrafficRowExpanded(i) }"
            >
              <button
                type="button"
                class="traffic-row__summary"
                :aria-expanded="isTrafficRowExpanded(i)"
                :aria-controls="`traffic-detail-${day.day}-${i}`"
                @click="toggleTrafficRow(i)"
              >
                <span class="traffic-row__route">
                  <span
                    class="traffic-row__place"
                    :title="cleanDisplayText(seg.from)"
                  >{{ cleanDisplayText(seg.from) }}</span>
                  <span class="traffic-row__arrow">→</span>
                  <span
                    class="traffic-row__place"
                    :title="cleanDisplayText(seg.to)"
                  >{{ cleanDisplayText(seg.to) }}</span>
                </span>
                <span class="traffic-row__info">
                  <span
                    class="traffic-row__mode"
                    :class="{ 'traffic-row__mode--estimated': isEstimatedTraffic(seg) }"
                  >
                    {{ modeIcon(seg.mode) }} {{ trafficModeLabel(seg) }}
                  </span>
                  <span
                    v-if="seg.distance_km"
                    class="traffic-row__dist"
                  >{{ Number(seg.distance_km).toFixed(1) }}km</span>
                  <span class="traffic-row__time">{{ seg.time_min }}min</span>
                  <span
                    v-if="seg.cost"
                    class="traffic-row__cost"
                  >¥{{ seg.cost }}</span>
                  <span
                    class="traffic-row__chevron"
                    aria-hidden="true"
                  >⌄</span>
                </span>
              </button>

              <Transition name="traffic-detail">
                <div
                  v-if="isTrafficRowExpanded(i)"
                  :id="`traffic-detail-${day.day}-${i}`"
                  class="traffic-row__details"
                >
                  <div class="traffic-row__full-route">
                    {{ cleanDisplayText(seg.from) }} → {{ cleanDisplayText(seg.to) }}
                  </div>

                  <div
                    v-if="isEstimatedTraffic(seg)"
                    class="traffic-row__estimate-note"
                  >
                    该路段为距离、时间和费用估算，暂无精确线路数据。
                  </div>

                  <template v-else-if="routePlans(seg).length">
                    <section
                      v-for="(routePlan, planIndex) in routePlans(seg)"
                      :key="planIndex"
                      class="traffic-plan"
                      :class="{ 'traffic-plan--recommended': planIndex === 0 }"
                    >
                      <div class="traffic-plan__header">
                        <strong>{{ planLabel(planIndex) }}</strong>
                        <span
                          v-if="planIndex === 0"
                          class="traffic-plan__recommended-badge"
                        >推荐</span>
                        <span class="traffic-plan__metrics">
                          {{ formatSeconds(routePlan.duration) }}
                          <template v-if="routePlan.cost != null"> · ¥{{ routePlan.cost }}</template>
                          <template v-if="routePlan.walking_distance"> · 步行{{ formatMeters(routePlan.walking_distance) }}</template>
                        </span>
                      </div>
                      <div
                        v-if="routePlan.segments?.length"
                        class="traffic-plan__steps"
                      >
                        <div
                          v-for="(step, stepIndex) in routePlan.segments"
                          :key="stepIndex"
                          class="traffic-plan__step"
                        >
                          <span class="traffic-plan__step-icon">{{ stepIcon(step) }}</span>
                          <span class="traffic-plan__step-body">
                            <strong>{{ stepTitle(step) }}</strong>
                            <span
                              v-if="stepRoute(step)"
                              class="traffic-plan__step-route"
                            >{{ stepRoute(step) }}</span>
                            <span
                              v-if="stepMeta(step)"
                              class="traffic-plan__step-meta"
                            >{{ stepMeta(step) }}</span>
                          </span>
                        </div>
                      </div>
                      <p
                        v-else
                        class="traffic-plan__empty"
                      >
                        该方案暂无分步信息。
                      </p>
                    </section>
                  </template>

                  <div
                    v-else
                    class="traffic-row__empty-detail"
                  >
                    {{ cleanDisplayText(seg.detail) || '暂无精确线路数据。' }}
                  </div>
                </div>
              </Transition>
            </div>
            <div class="traffic-row traffic-row--total">
              <span class="traffic-row__label">合计</span>
              <span class="traffic-row__info">
                <span class="traffic-row__time">{{ trafficTotal.time }}min</span>
                <span class="traffic-row__cost">¥{{ trafficTotal.cost }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 内嵌小地图 -->
        <div
          v-if="mapMarkers.length"
          class="day-card__map"
        >
          <MapContainer
            :markers="mapMarkers"
            :polyline="mapRoutePath.length > 1 ? [mapRoutePath] : []"
            :center="mapMarkers[0]?.position || [112.98, 28.19]"
            :zoom="13"
          />
        </div>

        <!-- 日总结 -->
        <div class="day-card__summary">
          <p>{{ day.day_summary }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.day-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-float);
  overflow: hidden;
  transition: all var(--dur-normal) var(--ease-in-out);
  margin-bottom: var(--space-4);
}

.day-card__header {
  display: flex;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  cursor: pointer;
  user-select: none;
  transition: background var(--dur-fast);
}
.day-card__header:hover {
  background: var(--color-brand-50);
}

.day-card__day-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.day-card__day-label {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-brand-500);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-body-sm);
  font-weight: var(--fw-bold);
}

.day-card__date-info {
  display: flex;
  flex-direction: column;
}

.day-card__date {
  font-size: var(--text-body);
  font-weight: var(--fw-semibold);
  color: var(--color-text-primary);
}

.day-card__date-label {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.day-card__summary-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.day-card__weather {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  padding: 2px 8px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-pill);
}

.day-card__day-cost {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-semibold);
  color: var(--color-brand-600);
}

.day-card__toggle {
  margin-left: var(--space-3);
  color: var(--color-text-tertiary);
  transition: transform var(--dur-fast);
}

/* 时间轴 */
.day-card__timeline {
  position: relative;
  padding: var(--space-2) 0;
}
.day-card__timeline::before {
  content: '';
  position: absolute;
  left: 52px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

/* 住宿卡片 */
.day-card__accommodation {
  padding: var(--space-3) var(--space-5);
}

.accommodation-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-type-accommodation-bg);
  border-radius: var(--radius-sm);
}

.accommodation-card__icon {
  color: var(--color-type-accommodation);
  flex-shrink: 0;
}

.accommodation-card__info {
  flex: 1;
}

.accommodation-card__name {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.accommodation-card__address {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.accommodation-card__price {
  font-size: var(--text-body);
  font-weight: var(--fw-bold);
  color: var(--color-brand-600);
}

.accommodation-card__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}

.accommodation-card__rating {
  font-size: var(--text-small);
  color: var(--color-gold, #D4A857);
  white-space: nowrap;
}

/* 餐饮 */
.day-card__meals {
  padding: var(--space-3) var(--space-5);
}

.day-card__section-label {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.meal-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-type-food-bg);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.meal-item__icon {
  color: var(--color-type-food);
  flex-shrink: 0;
}

.meal-item__info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.meal-item__restaurant {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.meal-item__dish {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.meal-item__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}

.meal-item__price {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-bold);
  color: var(--color-brand-600);
  white-space: nowrap;
}

.meal-item__reason {
  font-size: var(--text-tiny);
  color: var(--color-text-tertiary);
  margin: 0;
  text-align: right;
  line-height: 1.3;
}

/* 交通明细 */
.day-card__traffic {
  padding: var(--space-3) var(--space-5);
}
.traffic-table {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.traffic-row {
  border-bottom: 1px solid var(--color-border-light);
}
.traffic-row:last-child { border-bottom: none; }
.traffic-row__summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.traffic-row__summary:hover { background: var(--color-brand-50); }
.traffic-row__summary:focus-visible { outline: 2px solid var(--color-brand-400); outline-offset: -2px; }
.traffic-row--total {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-brand-50);
  font-weight: 600;
}
.traffic-row__route {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.traffic-row__place {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text-primary);
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.traffic-row--expanded .traffic-row__place { display: block; overflow: visible; }
.traffic-row__arrow { font-size: 11px; color: var(--color-text-tertiary); flex-shrink: 0; }
.traffic-row__info {
  display: flex; align-items: center; gap: var(--space-2);
  margin-left: var(--space-3);
  flex-shrink: 0;
}
.traffic-row__mode { font-size: 12px; color: var(--color-text-secondary); white-space: nowrap; }
.traffic-row__mode--estimated { color: var(--color-warning); }
.traffic-row__dist { font-size: 11px; color: var(--color-text-tertiary); }
.traffic-row__time { font-size: 12px; color: var(--color-text-tertiary); }
.traffic-row__cost { font-size: 12px; font-weight: 500; color: var(--color-brand-600); min-width: 32px; text-align: right; }
.traffic-row__label { font-size: 12px; color: var(--color-text-secondary); }
.traffic-row__chevron { color: var(--color-text-tertiary); font-size: 16px; transition: transform var(--dur-fast); }
.traffic-row--expanded .traffic-row__chevron { transform: rotate(180deg); }
.traffic-row__details { padding: 0 var(--space-3) var(--space-3); }
.traffic-row__full-route { padding: var(--space-2) 0; color: var(--color-text-primary); font-size: 12px; font-weight: 600; line-height: 1.5; overflow-wrap: anywhere; }
.traffic-row__estimate-note,
.traffic-row__empty-detail { padding: var(--space-3); border-radius: var(--radius-sm); color: var(--color-text-secondary); background: var(--color-brand-50); font-size: 12px; line-height: 1.5; }
.traffic-row__estimate-note { color: var(--color-warning); }
.traffic-plan { margin-top: var(--space-2); padding: var(--space-3); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); background: var(--color-bg-card); }
.traffic-plan--recommended { border-color: var(--color-brand-300); background: var(--color-brand-50); }
.traffic-plan__header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
.traffic-plan__header strong { color: var(--color-text-primary); font-size: 13px; }
.traffic-plan__recommended-badge { padding: 1px 7px; border-radius: 999px; color: var(--color-brand-700); background: var(--color-brand-100); font-size: 10px; }
.traffic-plan__metrics { margin-left: auto; color: var(--color-text-tertiary); font-size: 11px; white-space: nowrap; }
.traffic-plan__steps { display: flex; flex-direction: column; gap: var(--space-2); }
.traffic-plan__step { display: flex; gap: var(--space-2); min-width: 0; }
.traffic-plan__step-icon { flex: 0 0 20px; text-align: center; }
.traffic-plan__step-body { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 2px; }
.traffic-plan__step-body strong { color: var(--color-text-primary); font-size: 12px; overflow-wrap: anywhere; }
.traffic-plan__step-route { color: var(--color-text-secondary); font-size: 12px; overflow-wrap: anywhere; }
.traffic-plan__step-meta { color: var(--color-text-tertiary); font-size: 11px; }
.traffic-plan__empty { margin: 0; color: var(--color-text-tertiary); font-size: 12px; }
.traffic-detail-enter-active,
.traffic-detail-leave-active { transition: opacity var(--dur-fast), transform var(--dur-fast); }
.traffic-detail-enter-from,
.traffic-detail-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 720px) {
  .day-card__traffic { padding-left: var(--space-3); padding-right: var(--space-3); }
  .traffic-row__summary { grid-template-columns: 1fr; gap: var(--space-2); }
  .traffic-row__info { margin-left: 0; flex-wrap: wrap; }
  .traffic-plan__header { align-items: flex-start; flex-wrap: wrap; }
  .traffic-plan__metrics { width: 100%; margin-left: 0; }
}

/* 内嵌小地图 */
.day-card__map {
  height: 200px;
  margin: var(--space-3) var(--space-5);
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
}

/* 日总结 */
.day-card__summary {
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--color-border-light);
}

.day-card__summary p {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: 0;
  font-style: italic;
}

/* 展开折叠动画 */
.expand-enter-active {
  transition: all 0.3s var(--ease-out-expo);
  overflow: hidden;
}
.expand-leave-active {
  transition: all 0.2s var(--ease-in-out);
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
