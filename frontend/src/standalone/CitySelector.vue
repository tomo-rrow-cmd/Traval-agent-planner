<script setup lang="ts">
import { ref } from 'vue'
import { useCityMatch } from './useCityMatch'
import type { CityScores } from './types'

const emit = defineEmits<{
  select: [text: string]
}>()

const { selection, setDim, topCities, DIM_CONFIGS } = useCityMatch()

const showPopup = ref(false)
const popupRef = ref<HTMLElement | null>(null)
const hoverTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function onButtonEnter() {
  hoverTimer.value = setTimeout(() => { showPopup.value = true }, 150)
}
function onButtonLeave() {
  if (hoverTimer.value) { clearTimeout(hoverTimer.value); hoverTimer.value = null }
  scheduleHide()
}
function onPopupEnter() {
  if (hoverTimer.value) { clearTimeout(hoverTimer.value); hoverTimer.value = null }
}
function onPopupLeave() {
  scheduleHide()
}
function scheduleHide() {
  setTimeout(() => {
    // delay to allow mouse to move into popup
    if (!popupRef.value?.matches(':hover')) {
      showPopup.value = false
    }
  }, 200)
}

/** 点击城市：自动填入聊天框 */
function selectCity(name: string, _tagline: string) {
  emit('select', name)
  showPopup.value = false
}

/** 获取 toggle 维度的选中态 */
function isToggleOn(key: string) {
  return selection.value[key as keyof CityScores] === 2
}

const levelStyle = (key: string, idx: number) => {
  const v = selection.value[key as keyof CityScores]
  if (v === undefined) return ''
  return v === idx ? 'is-active' : ''
}
</script>

<template>
  <div class="cs-root">
    <!-- 触发按钮 -->
    <button
      class="cs-trigger"
      title="按偏好匹配城市"
      @mouseenter="onButtonEnter"
      @mouseleave="onButtonLeave"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
        <circle
          cx="12"
          cy="10"
          r="3"
        />
      </svg>
      <span>目的地</span>
    </button>

    <!-- 悬浮弹窗 -->
    <Transition name="cs-fade">
      <div
        v-if="showPopup"
        ref="popupRef"
        class="cs-popup"
        @mouseenter="onPopupEnter"
        @mouseleave="onPopupLeave"
      >
        <!-- 左栏：属性选择 -->
        <div class="cs-left">
          <div class="cs-title">
            选择你的偏好
          </div>

          <div class="cs-section">
            <div class="cs-section-title">
              城市气质
            </div>
            <div
              v-for="cfg in DIM_CONFIGS.filter(d => ['modern','nature','urban','culture'].includes(d.key))"
              :key="cfg.key"
              class="cs-row"
            >
              <span class="cs-label">{{ cfg.label }}</span>
              <div class="cs-options">
                <button
                  v-for="(lv, i) in (cfg.levels ?? [])"
                  :key="i"
                  class="cs-opt"
                  :class="levelStyle(cfg.key, i)"
                  @click="setDim(cfg.key, selection[cfg.key] === i ? -1 : i)"
                >
                  {{ lv }}
                </button>
              </div>
            </div>
          </div>

          <div class="cs-section">
            <div class="cs-section-title">
              口味偏好 <span class="cs-hint">（可多选）</span>
            </div>
            <div class="cs-toggles">
              <button
                v-for="cfg in DIM_CONFIGS.filter(d => ['sour','sweet','salty','spicy'].includes(d.key))"
                :key="cfg.key"
                class="cs-tag"
                :class="{ 'is-on': isToggleOn(cfg.key) }"
                @click="setDim(cfg.key, isToggleOn(cfg.key) ? -1 : 2)"
              >
                {{ cfg.label }}
              </button>
            </div>
          </div>

          <div class="cs-section">
            <div class="cs-section-title">
              气候与规模
            </div>
            <div
              v-for="cfg in DIM_CONFIGS.filter(d => ['summer','scale'].includes(d.key))"
              :key="cfg.key"
              class="cs-row"
            >
              <span class="cs-label">{{ cfg.label }}</span>
              <div class="cs-options">
                <button
                  v-for="(lv, i) in (cfg.levels ?? [])"
                  :key="i"
                  class="cs-opt"
                  :class="levelStyle(cfg.key, i)"
                  @click="setDim(cfg.key, selection[cfg.key] === i ? -1 : i)"
                >
                  {{ lv }}
                </button>
              </div>
            </div>
          </div>

          <div class="cs-section">
            <div class="cs-section-title">
              热度
            </div>
            <div
              v-for="cfg in DIM_CONFIGS.filter(d => d.key === 'popular')"
              :key="cfg.key"
              class="cs-row"
            >
              <span class="cs-label">{{ cfg.label }}</span>
              <div class="cs-options">
                <button
                  v-for="(lv, i) in (cfg.levels ?? [])"
                  :key="i"
                  class="cs-opt"
                  :class="levelStyle(cfg.key, i)"
                  @click="setDim(cfg.key, selection[cfg.key] === i ? -1 : i)"
                >
                  {{ lv }}
                </button>
              </div>
            </div>
          </div>

          <div class="cs-section">
            <div class="cs-section-title">
              自然特色 <span class="cs-hint">（可多选）</span>
            </div>
            <div class="cs-toggles">
              <button
                v-for="cfg in DIM_CONFIGS.filter(d => ['mountain','sea','lake'].includes(d.key))"
                :key="cfg.key"
                class="cs-tag"
                :class="{ 'is-on': isToggleOn(cfg.key) }"
                @click="setDim(cfg.key, isToggleOn(cfg.key) ? -1 : 2)"
              >
                {{ cfg.label }}
              </button>
            </div>
          </div>
        </div>

        <!-- 右栏：匹配城市 -->
        <div class="cs-right">
          <div class="cs-title">
            推荐目的地 <span class="cs-count">({{ selection && Object.keys(selection).length > 0 ? '按偏好' : '热门' }})</span>
          </div>
          <div class="cs-cities">
            <button
              v-for="city in topCities"
              :key="city.name"
              class="cs-city-card"
              @click="selectCity(city.name, city.tagline)"
            >
              <div class="cs-city-name">
                {{ city.name }}
              </div>
              <div class="cs-city-tagline">
                {{ city.tagline }}
              </div>
              <div class="cs-city-match">
                <span
                  class="cs-match-bar"
                  :style="{ width: (city.match * 100) + '%' }"
                />
                <span class="cs-match-pct">{{ Math.round(city.match * 100) }}%</span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.cs-root { position: relative; display: inline-flex; }

.cs-trigger {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: var(--color-bg-card);
  color: var(--color-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.cs-trigger:hover {
  border-color: var(--color-brand-300);
  color: var(--color-brand-600);
  background: var(--color-brand-50);
}

/* ===== 弹窗 ===== */
.cs-popup {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  display: flex;
  width: 780px;
  max-height: 520px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-drawer, 0 8px 40px rgba(0,0,0,0.12));
  overflow: hidden;
  z-index: var(--z-drawer, 1000);
}

.cs-left {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  border-right: 1px solid var(--color-border-light);
}

.cs-right {
  width: 280px;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cs-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 14px;
}
.cs-count { font-weight: 400; font-size: 12px; color: var(--color-text-tertiary); }
.cs-hint { font-weight: 400; font-size: 11px; color: var(--color-text-tertiary); }

.cs-section { margin-bottom: 14px; }
.cs-section-title {
  font-size: 12px; font-weight: 600; color: var(--color-text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 8px;
}

/* 行 */
.cs-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 0;
}
.cs-label {
  font-size: 13px; color: var(--color-text-secondary);
  min-width: 72px;
}

/* 选项按钮（level/single） */
.cs-options { display: flex; gap: 4px; }
.cs-opt {
  padding: 3px 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.cs-opt:hover { border-color: var(--color-brand-300); color: var(--color-brand-500); }
.cs-opt.is-active {
  background: var(--color-brand-500);
  border-color: var(--color-brand-500);
  color: #fff;
}

/* toggle 标签 */
.cs-toggles { display: flex; gap: 8px; flex-wrap: wrap; }
.cs-tag {
  padding: 4px 16px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.cs-tag:hover { border-color: var(--color-brand-300); color: var(--color-brand-500); }
.cs-tag.is-on {
  background: var(--color-brand-50);
  border-color: var(--color-brand-500);
  color: var(--color-brand-600);
}

/* ===== 城市卡片 ===== */
.cs-cities { display: flex; flex-direction: column; gap: 6px; }

.cs-city-card {
  display: flex; flex-direction: column; gap: 2px;
  padding: 10px 14px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  width: 100%;
}
.cs-city-card:hover {
  border-color: var(--color-brand-300);
  background: var(--color-brand-50);
  transform: translateX(2px);
}
.cs-city-name { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.cs-city-tagline { font-size: 11px; color: var(--color-text-tertiary); }
.cs-city-match { position: relative; height: 4px; border-radius: 2px; background: var(--color-bg-tertiary); margin-top: 4px; overflow: hidden; }
.cs-match-bar { position: absolute; top: 0; left: 0; height: 100%; border-radius: 2px; background: var(--color-brand-400); transition: width 0.3s; }
.cs-match-pct { display: none; }

/* 动画 */
.cs-fade-enter-active { transition: all 0.2s ease-out; }
.cs-fade-leave-active { transition: all 0.15s ease-in; }
.cs-fade-enter-from { opacity: 0; transform: translateY(8px); }
.cs-fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
