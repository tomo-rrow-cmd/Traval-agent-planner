<script setup lang="ts">
/* ============================================================
   WeatherForecast — 天气预报横向滚动卡片
   渲染 PlanDetail.weather_forecast 字段
   每日行程卡片也可内联显示当天的天气
   ============================================================ */

import { computed } from 'vue'
import type { WeatherForecast as WeatherForecastType } from '@/types/plan'

const props = defineProps<{
  forecasts: WeatherForecastType[]
  /** 如果指定，只显示该天数的预报（从第1天开始） */
  dayLimit?: number
}>()

/** 天气图标映射 */
const weatherIcon: Record<string, string> = {
  '晴': '☀️',
  '多云': '⛅',
  '阴': '☁️',
  '小雨': '🌦️',
  '中雨': '🌧️',
  '大雨': '🌧️',
  '雷阵雨': '⛈️',
  '阵雨': '🌦️',
  '雪': '❄️',
  '小雪': '🌨️',
  '中雪': '❄️',
  '雾': '🌫️',
  '霾': '🌫️',
}

function getIcon(weather: string): string {
  for (const [key, icon] of Object.entries(weatherIcon)) {
    if (weather.includes(key)) return icon
  }
  return '🌤️'
}

function getAQILabel(aqi: number | null | undefined): string {
  if (aqi == null) return ''
  if (aqi <= 50) return '优'
  if (aqi <= 100) return '良'
  if (aqi <= 150) return '轻度'
  if (aqi <= 200) return '中度'
  return '重度'
}

const dayLabels = ['第一天', '第二天', '第三天', '第四天', '第五天', '第六天', '第七天']

const displayForecasts = computed(() => {
  const limit = props.dayLimit ?? props.forecasts.length
  return props.forecasts.slice(0, limit)
})
</script>

<template>
  <div
    v-if="forecasts.length"
    class="weather-forecast"
  >
    <h3 class="block-section-title">
      <span class="weather-forecast__title-icon">🌤️</span>
      天气预报
    </h3>
    <div class="weather-forecast__scroll">
      <div
        v-for="(f, i) in displayForecasts"
        :key="i"
        class="weather-forecast__card"
        :class="{
          'weather-forecast__card--hot': (f.temp_high ?? 0) >= 35,
          'weather-forecast__card--cold': (f.temp_high ?? 30) <= 10,
          'weather-forecast__card--rain': f.weather && (f.weather.includes('雨') || f.weather.includes('雪')),
        }"
      >
        <div class="weather-forecast__day">
          {{ dayLabels[i] || `第${i + 1}天` }}
        </div>
        <div class="weather-forecast__date">
          {{ f.date || '' }}
        </div>
        <div class="weather-forecast__icon">
          {{ getIcon(f.weather) }}
        </div>
        <div class="weather-forecast__weather">
          {{ f.weather || '' }}
        </div>
        <div class="weather-forecast__temps">
          <span class="weather-forecast__high">{{ f.temp_high ?? '-' }}°</span>
          <span class="weather-forecast__sep">/</span>
          <span class="weather-forecast__low">{{ f.temp_low ?? '-' }}°</span>
        </div>
        <div class="weather-forecast__extras">
          <span
            v-if="f.wind"
            class="weather-forecast__extra"
          >💨 {{ f.wind }}</span>
          <span
            v-if="f.humidity != null"
            class="weather-forecast__extra"
          >💧 {{ f.humidity }}%</span>
          <span
            v-if="f.precipitation"
            class="weather-forecast__extra"
          >🌧️ {{ f.precipitation }}mm</span>
          <span
            v-if="f.aqi != null"
            class="weather-forecast__extra"
            :class="`weather-forecast__aqi--${getAQILabel(f.aqi)}`"
          >
            🌫️ {{ getAQILabel(f.aqi) }}
          </span>
        </div>
        <div
          v-if="f.advice"
          class="weather-forecast__advice"
        >
          {{ f.advice }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.weather-forecast {
  margin: 24px 0;
}

.block-section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.weather-forecast__title-icon {
  font-size: 18px;
  line-height: 1;
}

.weather-forecast__scroll {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 8px;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}

.weather-forecast__card {
  flex: 0 0 160px;
  scroll-snap-align: start;
  padding: 14px 12px;
  border-radius: 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  text-align: center;
  min-width: 0;
  transition: box-shadow var(--dur-fast);
}
.weather-forecast__card:hover {
  box-shadow: var(--shadow-float);
}

/* 天气主题色提示 */
.weather-forecast__card--hot {
  background: linear-gradient(180deg, #FFF5F0 0%, var(--color-bg-card) 100%);
  border-color: #FFD4BC;
}
.weather-forecast__card--cold {
  background: linear-gradient(180deg, #F0F8FF 0%, var(--color-bg-card) 100%);
  border-color: #BCE0FF;
}
.weather-forecast__card--rain {
  background: linear-gradient(180deg, #F0F8FF 0%, var(--color-bg-card) 100%);
  border-color: #C8E6F0;
}

.weather-forecast__day {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-brand-600);
  margin-bottom: 2px;
}

.weather-forecast__date {
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-bottom: 8px;
}

.weather-forecast__icon {
  font-size: 32px;
  line-height: 1.2;
  margin-bottom: 4px;
}

.weather-forecast__weather {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.weather-forecast__temps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-bottom: 8px;
}

.weather-forecast__high {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.weather-forecast__sep {
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.weather-forecast__low {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-tertiary);
}

.weather-forecast__extras {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  margin-bottom: 6px;
}

.weather-forecast__extra {
  font-size: 11px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  padding: 1px 6px;
  background: var(--color-bg-secondary);
  border-radius: 999px;
}

.weather-forecast__advice {
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  padding: 4px 8px;
  background: var(--color-brand-50);
  border-radius: 6px;
  margin-top: 4px;
}
</style>
