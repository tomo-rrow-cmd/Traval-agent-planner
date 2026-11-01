<script setup lang="ts">
/* ============================================================
   专业 SVG 图标合集
   线性风格，2px 描边，圆头端点，24x24 视口
   参考 Layla / Mindtrip / Booking.com 的图标体系
   ============================================================ */

import { computed } from 'vue'

const props = withDefaults(defineProps<{
  name: string
  size?: number
}>(), {
  size: 24,
})

const iconPaths: Record<string, string> = {
  compass: 'M12 2a10 10 0 1 0 10 10M12 2a10 10 0 0 1 10 10M12 2v20M2 12h20M12 8v2M12 14v2M8 12h2M14 12h2',
  map: 'M3 7v14l6-3 6 3 6-3V4l-6 3-6-3-6 3zM9 4v14M15 7v14',
  plane: 'M22 2l-7 20-4-9-9-4 20-7zM11 13l5-5',
  sparkle: 'M12 2l1.5 6.5L20 10l-6.5 1.5L12 18l-1.5-6.5L4 10l6.5-1.5L12 2zM12 18v4M18 12h4M6 12H2M12 6V2',
  grid: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  user: 'M16 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM4 20c0-4 3.6-6 8-6s8 2 8 6',
  refresh: 'M1 12a11 11 0 0 1 20-7M23 12a11 11 0 0 1-20 7M1 1v6h6M23 23v-6h-6',
  mountain: 'M2 22l6-10 4 6 4-8 6 12H2zM8 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  lake: 'M2 14c2 0 4-3 8-3s6 3 8 3 4-3 8-3M2 18c2 0 4-3 8-3s6 3 8 3',
  landmark: 'M6 22v-8M10 22v-8M14 22v-8M18 22v-8M4 14l8-8 8 8M12 2v4',
  beach: 'M2 22h20M6 18c0-6 12-6 12 0M10 14c1-3 6-3 7 0',
  city: 'M4 22V8l6-4v18M4 22h16M10 22V4l4-2v20M16 22V10l4-2v14M4 14h4M14 14h4',
  pine: 'M12 2l-5 8h3v4h4v-4h3l-5-8zM10 14h4v2h-4zM11 16h2v4h-2z',
  chat: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10zM8 9h8M8 13h6',
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  wallet: 'M21 6v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2zM3 10h6a3 3 0 0 1 0 6H3',
  star: 'M12 2l2.4 7.2H22l-6 4.8 2.4 7.2L12 17.6 5.6 21.2 8 14l-6-4.8h7.6L12 2z',
  share: 'M18 6a3 3 0 1 0-6 0 3 3 0 0 0 6 0zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 21a3 3 0 1 0-6 0 3 3 0 0 0 6 0zM13.5 12l-4-1.5M13.5 12l-4 1.5',
  download: 'M12 2v12M8 10l4 4 4-4M4 18v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2',
  replace: 'M17 2l4 4-4 4M3 10V8a4 4 0 0 1 4-4h4M7 22l-4-4 4-4M21 14v2a4 4 0 0 1-4 4h-4',
  delete: 'M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M10 11v6M14 11v6',
  close: 'M18 6L6 18M6 6l12 12',
  'arrow-right': 'M5 12h14M13 5l7 7-7 7',
  check: 'M5 13l4 4L19 7',
  sun: 'M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z',
  moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  menu: 'M3 6h18M3 12h18M3 18h18',
  pin: 'M12 22s8-6 8-12a8 8 0 1 0-16 0c0 6 8 12 8 12zM12 14a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  'arrow-up': 'M12 19V5M5 12l7-7 7 7',
}

const svgContent = computed(() => {
  const raw = iconPaths[props.name]
  if (!raw) return ''
  // Each 'M' starts a new path element, but we can just render one SVGG element with all paths
  return raw
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      v-for="(d, i) in (svgContent || '').split('M').filter(Boolean).map(p => 'M' + p.trim())"
      :key="i"
      :d="d"
    />
  </svg>
</template>
