<script setup lang="ts">
/* ============================================================
   PlanMap — 方案地图（包装 MapContainer）
   展示当天行程路线和 POI 标注
   ============================================================ */

import { computed } from 'vue'
import type { DailyItinerary, PlanResponse } from '@/types/plan'
import MapContainer from '@/components/map/MapContainer.vue'
import { buildDailyMapData } from '@/utils/planMap'

const props = defineProps<{
  plan: PlanResponse
  activeDay: number
}>()

const currentDay = computed<DailyItinerary | undefined>(() =>
  props.plan.daily_itinerary?.find((d) => d.day === props.activeDay),
)

const mapData = computed(() => {
  const day = currentDay.value
  const mealPlan = (props.plan as any).meal_plan || []
  const meals = (day as any)?.meals?.length
    ? (day as any).meals
    : (mealPlan.find((mealDay: any) => Number(mealDay.day) === Number(day?.day))?.meals || [])
  const hotelPlan = (props.plan as any).hotel_plan || {}
  const recommendations = hotelPlan.recommendations || []
  const selectedHotel = hotelPlan.selected_hotel
    || recommendations.find((hotel: any) => hotel.name === hotelPlan.selected)
    || recommendations[0]
  return buildDailyMapData(day ? { ...day, meals } : null, selectedHotel)
})
</script>

<template>
  <div class="plan-map">
    <div class="plan-map__header">
      <span class="plan-map__label">📍 第{{ activeDay }}天路线</span>
      <span
        v-if="currentDay"
        class="plan-map__date"
      >{{ currentDay.date }}</span>
    </div>
    <div class="plan-map__container">
      <MapContainer
        :center="mapData.centerPoint"
        :zoom="13"
        :markers="mapData.markers"
        :polyline="mapData.routePath.length > 1 ? [mapData.routePath] : []"
      />
    </div>
  </div>
</template>

<style scoped>
.plan-map {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.plan-map__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}

.plan-map__label {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.plan-map__date {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.plan-map__container {
  flex: 1;
  min-height: 360px;
}
</style>
