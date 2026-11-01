<script setup lang="ts">
/* ============================================================
   AppLogo — 品牌 Logo「归途之羽」
   单线连续闭环，象征旅程轨迹与无限可能
   ============================================================ */

withDefaults(defineProps<{
  size?: number
  type?: 'full' | 'icon' | 'wordmark'
}>(), {
  size: 32,
  type: 'icon',
})
</script>

<template>
  <!-- 纯图标 -->
  <svg
    v-if="type === 'icon'"
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class="app-logo"
  >
    <path
      d="M7 28 C7 28 18 28 24 22 C30 16 30 8 24 5 C18 2 10 6 8 14 C6 22 14 28 20 25 C26 22 26 16 22 13 C18 10 13 13 14 17 C15 21 19 20 20 18"
      stroke="currentColor"
      stroke-width="2.2"
      stroke-linecap="round"
      stroke-linejoin="round"
      fill="none"
      class="app-logo__path"
    />
  </svg>

  <!-- 全称：图标 + 品牌名 -->
  <div
    v-else-if="type === 'full'"
    class="app-logo__full"
    :style="{ gap: size * 0.25 + 'px' }"
  >
    <svg
      :width="size"
      :height="size"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      class="app-logo"
    >
      <path
        d="M7 28 C7 28 18 28 24 22 C30 16 30 8 24 5 C18 2 10 6 8 14 C6 22 14 28 20 25 C26 22 26 16 22 13 C18 10 13 13 14 17 C15 21 19 20 20 18"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
        stroke-linejoin="round"
        fill="none"
      />
    </svg>
    <span class="app-logo__wordmark">旅行者</span>
  </div>
</template>

<style scoped>
.app-logo {
  flex-shrink: 0;
  transition: color var(--dur-normal) var(--ease-in-out);
}

/* 悬停效果 */
.app-logo:hover .app-logo__path {
  animation: logoFloat 2s var(--ease-in-out) infinite;
}

@keyframes logoFloat {
  0%, 100% { stroke-dashoffset: 0; }
  50% { stroke-dashoffset: 2; }
}

.app-logo__full {
  display: flex;
  align-items: center;
}

.app-logo__wordmark {
  font-size: inherit;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--color-brand-600);
  white-space: nowrap;
}
</style>
