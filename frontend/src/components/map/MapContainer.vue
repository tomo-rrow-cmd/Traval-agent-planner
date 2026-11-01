<script setup lang="ts">
/* ============================================================
   MapContainer — 高德地图容器封装
   使用 @amap/amap-jsapi-loader 动态加载
   ============================================================ */

import { computed, createVNode, ref, render, onMounted, onUnmounted, watch, type Component } from 'vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import {
  CarOutlined,
  CoffeeOutlined,
  CustomerServiceOutlined,
  EnvironmentOutlined,
  HomeOutlined,
  RestOutlined,
  ShoppingOutlined,
} from '@ant-design/icons-vue'
import { MAP_CONFIG } from '@/config/map'
import { normalizeMapMarkerType, type PlanMapMarker, type PlanMapMarkerType } from '@/utils/planMap'

// 高德地图 AMap 全局类型声明
declare global {
  interface Window {
    AMap: any
    _AMapSecurityConfig?: { securityJsCode?: string }
  }
}

const props = withDefaults(defineProps<{
  center?: [number, number]
  zoom?: number
  markers?: PlanMapMarker[]
  polyline?: Array<[number, number][]>
  style?: string
  navType?: 'driving' | 'walking'
}>(), {
  center: () => MAP_CONFIG.center,
  zoom: MAP_CONFIG.zoom,
  markers: () => [],
  polyline: () => [],
  style: 'light',
  navType: 'driving',
})

const emit = defineEmits<{
  ready: [map: any]
  markerClick: [marker: any, index: number]
}>()

const containerRef = ref<HTMLDivElement>()
const mapRef = ref<any>(null)
const loaded = ref(false)
const loadError = ref(false)
const markersRef = ref<any[]>([])
const polylinesRef = ref<any[]>([])
const markerContentsRef = ref<HTMLElement[]>([])

interface MarkerVisual {
  label: string
  color: string
  icon: Component
}

const MARKER_VISUALS: Record<PlanMapMarkerType, MarkerVisual> = {
  accommodation: { label: '酒店', color: '#7C3AED', icon: HomeOutlined },
  attraction: { label: '景点', color: '#16856A', icon: EnvironmentOutlined },
  food: { label: '餐饮', color: '#C2410C', icon: CoffeeOutlined },
  transport: { label: '交通', color: '#2563EB', icon: CarOutlined },
  shopping: { label: '购物', color: '#A63A87', icon: ShoppingOutlined },
  entertainment: { label: '娱乐', color: '#9A6700', icon: CustomerServiceOutlined },
  rest: { label: '休息', color: '#64748B', icon: RestOutlined },
}

const markerLegend = computed(() => {
  const types = new Set(props.markers.map(marker => normalizeMapMarkerType(marker.type)))
  return Array.from(types).map(type => ({ type, ...MARKER_VISUALS[type] }))
})

onMounted(() => {
  loadMap()
})

onUnmounted(() => {
  destroyMap()
})

watch(() => props.center, (newCenter) => {
  if (mapRef.value && newCenter) {
    mapRef.value.setCenter(newCenter)
  }
})

watch(() => props.zoom, (newZoom) => {
  if (mapRef.value && newZoom) {
    mapRef.value.setZoom(newZoom)
  }
})

watch(() => props.markers, () => {
  updateMarkers()
}, { deep: true })

watch(() => props.polyline, () => {
  updatePolylines()
}, { deep: true })

async function loadMap() {
  try {
    // 高德 JSAPI 2.0 安全密钥配置
    if (MAP_CONFIG.securityJsCode) {
      window._AMapSecurityConfig = { securityJsCode: MAP_CONFIG.securityJsCode }
    }

    const AMap = await AMapLoader.load({
      key: MAP_CONFIG.key,
      version: MAP_CONFIG.version,
    })

    // 挂载到 window 供组件内其他方法使用
    window.AMap = AMap

    if (!containerRef.value) return

    // 初始化地图
    const map = new AMap.Map(containerRef.value, {
      zoom: props.zoom,
      center: props.center,
      mapStyle: props.style === 'dark' ? 'amap://styles/dark' : 'amap://styles/light',
      layers: [new AMap.TileLayer()],
      viewMode: '2D',
      showIndoorMap: false,
      zoomEnable: true,
      dragEnable: true,
    })

    mapRef.value = map
    loaded.value = true
    emit('ready', map)

    // 添加初始标记
    updateMarkers()
    // 添加初始路线
    updatePolylines()

    // 延迟触发 resize 避免容器大小问题
    setTimeout(() => map.resize(), 200)
  } catch (err) {
    console.error('地图加载失败:', err)
    loadError.value = true
  }
}

function updateMarkers() {
  if (!mapRef.value || !window.AMap) return

  clearMarkers()

  props.markers.forEach((m, index) => {
    const marker = new window.AMap.Marker({
      position: m.position,
      title: m.title,
      content: createMarkerContent(m),
      offset: new window.AMap.Pixel(-16, -32),
    })

    marker.on('click', () => {
      emit('markerClick', marker, index)
      showInfoWindow(marker, m)
    })

    mapRef.value.add(marker)
    markersRef.value.push(marker)
  })

  // 自动适配视野
  if (props.markers.length > 0) {
    mapRef.value.setFitView(null, false, [30, 30, 30, 30])
  }
}

function createMarkerContent(m: PlanMapMarker): HTMLElement {
  const type = normalizeMapMarkerType(m.type)
  const visual = MARKER_VISUALS[type]
  const element = document.createElement('div')
  Object.assign(element.style, {
    width: '32px',
    height: '32px',
    borderRadius: type === 'accommodation' ? '7px' : '50%',
    background: visual.color,
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.24)',
    border: '2px solid #fff',
    cursor: 'pointer',
  })
  element.setAttribute('role', 'img')
  element.setAttribute('aria-label', `${visual.label}: ${m.title || '未命名地点'}`)
  render(createVNode(visual.icon), element)
  markerContentsRef.value.push(element)
  return element
}

function escapeHtml(value?: string): string {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function showInfoWindow(marker: any, m: PlanMapMarker) {
  if (!window.AMap) return
  const info = new window.AMap.InfoWindow({
    content: `<div style="padding:8px 12px;font-size:13px;max-width:200px">
      <strong>${escapeHtml(m.title)}</strong>
      ${m.content ? `<p style="margin:4px 0 0;color:#666">${escapeHtml(m.content)}</p>` : ''}
    </div>`,
    offset: new window.AMap.Pixel(0, -30),
  })
  if (marker.openInfoWindow) {
    marker.openInfoWindow(info)
  } else {
    mapRef.value?.setInfoWindow(info)
  }
}

function clearMarkers() {
  markerContentsRef.value.forEach(element => render(null, element))
  markerContentsRef.value = []
  markersRef.value.forEach((m) => {
    mapRef.value?.remove(m)
  })
  markersRef.value = []
}

function updatePolylines() {
  if (!mapRef.value || !window.AMap) return

  polylinesRef.value.forEach((p) => mapRef.value?.remove(p))
  polylinesRef.value = []

  for (const path of props.polyline) {
    if (path.length < 2) continue

    // 先用途径点画出基础路线（途经点连线）
    const basePolyline = new window.AMap.Polyline({
      path,
      strokeColor: '#E8A87C',
      strokeWeight: 4,
      strokeOpacity: 0.7,
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true,
    })
    mapRef.value.add(basePolyline)
    polylinesRef.value.push(basePolyline)

    // 异步尝试获取高德真实驾车路线（失败不影响基础路线）
    tryCalculateDrivingRoute(path)
  }
}

/** 将 step.path 解析为 [lng, lat] 数组 */
function extractCoordsFromStep(step: any): Array<[number, number]> {
  const coords: Array<[number, number]> = []
  const rawPath = step.path || step.path_coords || []
  const path: any[] = Array.isArray(rawPath) ? rawPath : String(rawPath).split(';')
  for (const p of path) {
    if (typeof p === 'object' && p !== null && 'lng' in p && 'lat' in p && p.lng != null && p.lat != null) {
      coords.push([Number(p.lng), Number(p.lat)])
    } else if (Array.isArray(p) && p.length >= 2 && p[0] != null && p[1] != null) {
      coords.push([Number(p[0]), Number(p[1])])
    } else if (typeof p === 'string' && p.includes(',')) {
      const [lng, lat] = p.split(',').map(Number)
      if (lng && lat) coords.push([lng, lat])
    }
  }
  return coords
}

/** 单次驾车路线查询（起点→终点），返回坐标数组或 null */
function searchOneSegment(
  driving: any,
  from: [number, number],
  to: [number, number],
  timeoutMs: number = 8000,
): Promise<Array<[number, number]> | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      console.warn('[MapContainer] 分段路线超时:', from, to)
      resolve(null)
    }, timeoutMs)
    driving.search(from, to, (status: string, result: any) => {
      clearTimeout(timer)
      try {
        if (status === 'complete' && result.routes?.[0]?.steps) {
          const allCoords: Array<[number, number]> = []
          for (const step of result.routes[0].steps) {
            allCoords.push(...extractCoordsFromStep(step))
          }
          resolve(allCoords.length > 0 ? allCoords : null)
        } else {
          console.warn('[MapContainer] 分段路线未返回完整结果:', status, from, to)
          resolve(null)
        }
      } catch (err) {
        console.error('[MapContainer] 分段路线回调异常:', err)
        resolve(null)
      }
    })
  })
}

async function tryCalculateDrivingRoute(waypoints: Array<[number, number]>) {
  if (!window.AMap || waypoints.length < 2) {
    console.warn('[MapContainer] 路线规划跳过：', { hasAMap: !!window.AMap, waypointCount: waypoints.length })
    return
  }

  console.log('[MapContainer] 分段路线规划，途经点:', waypoints.length)

  // 确保 Driving 插件已加载
  if (!window.AMap.Driving) {
    console.log('[MapContainer] 正在加载 AMap.Driving 插件...')
    await new Promise<void>((resolve) => {
      window.AMap.plugin(['AMap.Driving'], () => resolve())
    })
    if (!window.AMap.Driving) {
      console.error('[MapContainer] AMap.Driving 插件加载失败')
      return
    }
  }

  try {
    const driving = new window.AMap.Driving({
      policy: window.AMap.DrivingPolicy.LEAST_TIME,
    })

    // 分段请求：A→B, B→C, C→D ...
    const segmentPromises: Promise<Array<[number, number]> | null>[] = []
    for (let i = 0; i < waypoints.length - 1; i++) {
      segmentPromises.push(
        searchOneSegment(driving, waypoints[i], waypoints[i + 1]),
      )
    }

    const segmentResults = await Promise.race([
      Promise.all(segmentPromises),
      new Promise<null[]>(resolve => setTimeout(() => resolve(segmentPromises.map(() => null)), 8000)),
    ])

    // 合并所有分段（跳过 null）
    const allCoords: Array<[number, number]> = []
    for (const seg of segmentResults) {
      if (seg && seg.length > 0) {
        // 去掉每段第一个点（和上段最后一个点重复）
        if (allCoords.length > 0) allCoords.pop()
        allCoords.push(...seg)
      }
    }

    if (allCoords.length > 0 && mapRef.value) {
      console.log('[MapContainer] 路线规划成功，总坐标点数:', allCoords.length)
      // 移除基础路线，绘制真实路线
      if (polylinesRef.value.length > 0) {
        const lastLine = polylinesRef.value[polylinesRef.value.length - 1]
        mapRef.value.remove(lastLine)
        polylinesRef.value.pop()
      }
      const realPolyline = new window.AMap.Polyline({
        path: allCoords,
        strokeColor: '#D85A30',
        strokeWeight: 5,
        strokeOpacity: 0.85,
        lineJoin: 'round',
        lineCap: 'round',
        showDir: true,
      })
      mapRef.value.add(realPolyline)
      polylinesRef.value.push(realPolyline)
    }
  } catch (e) {
    console.error('[MapContainer] 路线规划异常:', e)
  }
}

function destroyMap() {
  markersRef.value = []
  polylinesRef.value = []
  if (mapRef.value) {
    mapRef.value.destroy()
    mapRef.value = null
  }
}

defineExpose({
  getMap: () => mapRef.value,
  refresh: () => { loaded.value = false; loadMap() },
})
</script>

<template>
  <div class="map-container">
    <!-- 加载态 -->
    <div
      v-if="!loaded && !loadError"
      class="map-container__loading"
    >
      <div class="map-container__loading-spinner" />
      <p>地图加载中...</p>
    </div>

    <!-- 失败 fallback -->
    <div
      v-else-if="loadError"
      class="map-container__error"
    >
      <div class="map-container__error-icon">
        🗺️
      </div>
      <p class="map-container__error-text">
        地图加载失败
      </p>
      <p class="map-container__error-hint">
        请检查网络连接或 High德 API Key 配置
      </p>
      <a-button
        size="small"
        @click="loadMap"
      >
        重新加载
      </a-button>
    </div>

    <!-- 地图容器 -->
    <div
      ref="containerRef"
      class="map-container__map"
      :class="{ 'map-container__map--hidden': !loaded }"
    />

    <div
      v-if="loaded && markerLegend.length"
      class="map-container__legend"
      aria-label="地图标记图例"
    >
      <span
        v-for="item in markerLegend"
        :key="item.type"
        class="map-container__legend-item"
      >
        <span
          class="map-container__legend-icon"
          :style="{ backgroundColor: item.color, borderRadius: item.type === 'accommodation' ? '4px' : '50%' }"
        >
          <component :is="item.icon" />
        </span>
        <span>{{ item.label }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.map-container__map {
  width: 100%;
  height: 100%;
}
.map-container__map--hidden {
  opacity: 0;
  position: absolute;
}

.map-container__legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  max-width: calc(100% - 24px);
  padding: 7px 9px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
  color: #334155;
  font-size: 12px;
  line-height: 18px;
  pointer-events: none;
}

.map-container__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.map-container__legend-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: #fff;
  font-size: 11px;
}

/* 加载态 */
.map-container__loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  font-size: var(--text-body-sm);
  border-radius: var(--radius-md);
}

.map-container__loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 失败态 */
.map-container__error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background: var(--color-bg-secondary);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

.map-container__error-icon {
  font-size: 36px;
  margin-bottom: var(--space-1);
}

.map-container__error-text {
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-secondary);
  margin: 0;
}

.map-container__error-hint {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--space-3);
  text-align: center;
  max-width: 240px;
}
</style>
