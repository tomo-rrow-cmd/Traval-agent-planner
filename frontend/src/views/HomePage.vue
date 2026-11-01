<script setup lang="ts">
/* ============================================================
   HomePage — 杂志风格首页
   设计灵感：小地球旅行的诗意感 + Mindtrip 的视觉活力
   ============================================================ */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

// 热门目的地（本地风景照）
const destinations = [
  { name: '大理', tag: '风花雪月', color: '#7EB8DA', image: '/images/大理.jpg' },
  { name: '成都', tag: '天府之国', color: '#5B9B8C', image: '/images/成都.jpg' },
  { name: '杭州', tag: '江南印象', color: '#A8B5A0', image: '/images/杭州.jpg' },
  { name: '西安', tag: '千年古都', color: '#D4A857', image: '/images/西安.jpg' },
  { name: '三亚', tag: '热带天堂', color: '#E8A87C', image: '/images/三亚.jpg' },
  { name: '丽江', tag: '古城慢活', color: '#B58CB0', image: '/images/丽江.jpg' },
]

// 打字机效果
const typedText = ref('')
const fullText = '说走就走的旅行，从一句话开始'
let charIndex = 0

onMounted(() => {
  const timer = setInterval(() => {
    if (charIndex < fullText.length) {
      typedText.value += fullText[charIndex]
      charIndex++
    } else {
      clearInterval(timer)
    }
  }, 60)
})

function handleStart() {
  if (!authStore.isLoggedIn) {
    authStore.createAnonymousSession()
  }
  router.push('/chat')
}

function goToLogin() {
  uiStore.openLoginModal()
}

function handleImageError(e: Event) {
  const target = e.target as HTMLElement
  if (target) target.style.display = 'none'
}
</script>

<template>
  <div class="home-page">
    <!-- ===== HERO 杂志式大标题 ===== -->
    <section class="home-hero">
      <!-- 装饰背景元素 -->
      <div class="home-hero__deco">
        <div
          class="deco-circle deco-circle--lg deco-circle--brand"
          style="top: -60px; right: -80px;"
        />
        <div
          class="deco-circle deco-circle--md deco-circle--accent"
          style="bottom: 40px; left: -40px;"
        />
        <div
          class="deco-circle deco-circle--sm deco-circle--gold"
          style="top: 30%; left: 15%;"
        />
        <div
          class="deco-circle deco-circle--sm deco-circle--brand"
          style="bottom: 20%; right: 20%;"
        />
      </div>

      <div class="home-hero__content">
        <!-- 装饰标签 -->
        <div class="home-hero__badge">
          <span>✨ AI 驱动</span>
        </div>

        <!-- 主标题 — 杂志风格排版 -->
        <h1 class="home-hero__title">
          <span class="home-hero__title-line">旅行规划</span>
          <span class="home-hero__title-line text-gradient">从未如此简单</span>
        </h1>

        <!-- 打字机副标题 -->
        <p class="home-hero__subtitle">
          <span class="home-hero__cursor">{{ typedText }}<span class="home-hero__cursor-blink">|</span></span>
        </p>

        <div class="home-hero__actions">
          <button
            class="btn-primary-art"
            @click="handleStart"
          >
            <span class="btn-primary-art__text">开始规划旅程</span>
            <span class="btn-primary-art__arrow">→</span>
          </button>
          <button
            v-if="!authStore.isLoggedIn"
            class="btn-ghost-art"
            @click="goToLogin"
          >
            登录
          </button>
        </div>
      </div>
    </section>

    <!-- ===== 灵感探索区 ===== -->
    <section class="home-inspire">
      <div class="home-inspire__header">
        <h2 class="home-inspire__title">
          探索<span class="text-gradient">目的地</span>
        </h2>
        <hr class="divider-dotted">
      </div>

      <div class="home-inspire__grid">
        <div
          v-for="dest in destinations"
          :key="dest.name"
          class="dest-card"
          :style="{ '--accent': dest.color }"
          @click="handleStart"
        >
          <div class="dest-card__image">
            <img
              :src="dest.image"
              :alt="dest.name"
              class="dest-card__img"
              loading="lazy"
              @error="handleImageError"
            >
            <div class="dest-card__image-overlay" />
          </div>
          <div class="dest-card__body">
            <h3 class="dest-card__name">
              {{ dest.name }}
            </h3>
            <span class="dest-card__tag">{{ dest.tag }}</span>
          </div>
          <div
            class="dest-card__stripe"
            :style="{ background: dest.color }"
          />
        </div>
      </div>
    </section>

    <!-- ===== CTA 区 ===== -->
    <section class="home-cta">
      <div class="home-cta__bg-dots bg-dots" />
      <div class="home-cta__content">
        <h2 class="home-cta__title">
          准备好出发了吗？
        </h2>
        <p class="home-cta__subtitle font-decorative">
          每一次旅行，都值得被精心规划
        </p>
        <button
          class="btn-primary-art btn-primary-art--lg"
          @click="handleStart"
        >
          开始您的旅程
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  overflow-x: hidden;
}

/* ============================================================
   HERO — 杂志封面风格
   ============================================================ */

.home-hero {
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  overflow: hidden;
  background: var(--gradient-hero);
}

/* 装饰大圆 */
.home-hero__deco {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

/* 装饰标签 */
.home-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 14px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-brand-200);
  border-radius: 999px;
  font-size: 13px;
  color: var(--color-brand-600);
  margin-bottom: var(--space-6);
  backdrop-filter: blur(8px);
  animation: fadeInDown 0.6s var(--ease-out-expo);
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}

.home-hero__content {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 700px;
}

/* 杂志风格大标题 — 两行 */
.home-hero__title {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: var(--space-5);
  animation: fadeInUp 0.8s var(--ease-out-expo);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.home-hero__title-line {
  font-size: clamp(42px, 8vw, 72px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -1px;
  color: var(--color-text-primary);
}

.home-hero__title-line:last-child {
  font-size: clamp(38px, 7vw, 64px);
}

/* 打字机副标题 */
.home-hero__subtitle {
  font-size: clamp(16px, 2.5vw, 22px);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-8);
  min-height: 2em;
  animation: fadeInUp 0.8s var(--ease-out-expo) 0.2s both;
}

.home-hero__cursor-blink {
  display: inline-block;
  animation: blink 1s step-end infinite;
  color: var(--color-brand-500);
  font-weight: 100;
}

@keyframes blink {
  50% { opacity: 0; }
}

.home-hero__actions {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  align-items: center;
  animation: fadeInUp 0.8s var(--ease-out-expo) 0.4s both;
}

/* 艺术按钮 — 渐变 */
.btn-primary-art {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  padding: 14px 32px;
  border: none;
  background: var(--gradient-warm);
  color: white;
  font-size: 17px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s var(--ease-out-expo);
  box-shadow: var(--shadow-glow-brand);
}
.btn-primary-art:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(232, 168, 124, 0.35);
}
.btn-primary-art:active {
  transform: translateY(0);
}

.btn-primary-art--lg {
  padding: 18px 40px;
  font-size: 18px;
}

.btn-primary-art__arrow {
  transition: transform 0.3s var(--ease-out-expo);
}
.btn-primary-art:hover .btn-primary-art__arrow {
  transform: translateX(4px);
}

.btn-ghost-art {
  padding: 14px 24px;
  border: 2px solid var(--color-brand-300);
  background: transparent;
  color: var(--color-brand-600);
  font-size: 17px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s var(--ease-out-expo);
}
.btn-ghost-art:hover {
  background: var(--color-bg-card);
  border-color: var(--color-brand-500);
  transform: translateY(-2px);
}

/* ============================================================
   灵感探索区 — 目的地卡片
   ============================================================ */

.home-inspire {
  padding: 80px 24px 60px;
  max-width: var(--container-wide);
  margin: 0 auto;
  width: 100%;
}

.home-inspire__header {
  margin-bottom: var(--space-8);
  text-align: center;
}

.home-inspire__title {
  font-size: clamp(28px, 4vw, 36px);
  font-weight: 700;
  margin-bottom: var(--space-4);
}

.home-inspire__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-4);
}

.dest-card {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.4s var(--ease-out-expo);
  background: var(--color-bg-card);
  box-shadow: var(--shadow-float);
}

.dest-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: var(--shadow-glow-brand);
}

.dest-card__image {
  position: relative;
  height: 140px;
  overflow: hidden;
}

.dest-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s var(--ease-out-expo);
}
.dest-card:hover .dest-card__img {
  transform: scale(1.08);
}

.dest-card__image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(44,44,44,0.3) 100%);
}

.dest-card__stripe {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.dest-card__body {
  padding: var(--space-3) var(--space-4) var(--space-4);
  text-align: center;
}

.dest-card__name {
  font-size: var(--text-h4);
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.dest-card__tag {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

/* ============================================================
   特性区 — 杂志卡片
   ============================================================ */

.home-features {
  padding: 80px 24px;
  background: var(--gradient-brand-light);
}

.home-features__inner {
  max-width: var(--container-wide);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-10);
  align-items: center;
}

@media (max-width: 768px) {
  .home-features__inner {
    grid-template-columns: 1fr;
    gap: var(--space-8);
  }
}

.home-features__label {
  display: inline-block;
  padding: 4px 12px;
  background: var(--color-brand-100);
  color: var(--color-brand-700);
  font-size: 13px;
  font-weight: 600;
  border-radius: 999px;
  margin-bottom: var(--space-3);
}

.home-features__title {
  font-size: clamp(28px, 4vw, 38px);
  font-weight: 700;
  line-height: 1.2;
}

.home-features__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.feat-card {
  padding: var(--space-6);
  background: var(--color-bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-float);
  transition: all 0.4s var(--ease-out-expo);
  animation: fadeInUp 0.6s var(--ease-out-expo) both;
  animation-delay: var(--delay, 0s);
}
.feat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-card-hover);
}

.feat-card__icon {
  font-size: 32px;
  margin-bottom: var(--space-3);
  line-height: 1;
}

.feat-card__title {
  font-size: var(--text-body);
  font-weight: 700;
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
}

.feat-card__desc {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin: 0;
  line-height: 1.5;
}

/* ============================================================
   CTA 区
   ============================================================ */

.home-cta {
  position: relative;
  padding: 100px 24px;
  text-align: center;
  overflow: hidden;
}

.home-cta__bg-dots {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.home-cta__content {
  position: relative;
  z-index: 1;
}

.home-cta__title {
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 800;
  margin-bottom: var(--space-3);
  color: var(--color-text-primary);
}

.home-cta__subtitle {
  font-size: clamp(18px, 3vw, 24px);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-8);
  letter-spacing: 1px;
}
</style>
