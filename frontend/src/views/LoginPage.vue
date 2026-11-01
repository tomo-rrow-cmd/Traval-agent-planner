<script setup lang="ts">
/* ============================================================
   LoginPage — 沉浸式旅行灵感登录页
   左侧品牌展示+右侧登录表单
   ============================================================ */

import { useRouter } from 'vue-router'
import AppLogo from "@/components/brand/AppLogo.vue"
import IconTravel from '@/components/icons/IconTravel.vue'
import LoginForm from '@/components/auth/LoginForm.vue'

const router = useRouter()

// 旅行灵感目的地（本地风景照）
const destinations = [
  { name: '大理', image: '/images/大理.jpg', color: '#7EB8DA' },
  { name: '成都', image: '/images/成都.jpg', color: '#5B9B8C' },
  { name: '杭州', image: '/images/杭州.jpg', color: '#A8B5A0' },
  { name: '西安', image: '/images/西安.jpg', color: '#D4A857' },
  { name: '三亚', image: '/images/三亚.jpg', color: '#E8A87C' },
  { name: '丽江', image: '/images/丽江.jpg', color: '#B58CB0' },
]

// 功能亮点
const features = [
  { icon: 'sparkle', text: 'AI 智能规划', desc: '一句话生成完整行程' },
  { icon: 'grid', text: '多维度覆盖', desc: '交通/住宿/景点/美食/预算' },
  { icon: 'user', text: '个性定制', desc: '根据偏好量身定制' },
  { icon: 'refresh', text: '灵活修改', desc: '不满意随时调整优化' },
]

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-page__deco">
      <div
        class="deco-circle deco-circle--lg deco-circle--brand"
        style="top: -80px; left: 30%;"
      />
      <div
        class="deco-circle deco-circle--md deco-circle--accent"
        style="bottom: 15%; right: -40px;"
      />
      <div
        class="deco-circle deco-circle--sm deco-circle--gold"
        style="top: 40%; right: 25%;"
      />
      <div
        class="deco-circle deco-circle--sm deco-circle--brand"
        style="bottom: 40%; left: 5%;"
      />
    </div>

    <div class="login-page__container">
      <!-- ===== 左侧：品牌 + 灵感展示 ===== -->
      <div class="login-page__brand-section">
        <!-- 品牌标识 -->
        <div
          class="login-page__brand"
          style="cursor: pointer"
          @click="goHome"
        >
          <AppLogo
            :size="32"
            class="login-page__logo"
          />
          <span class="login-page__brand-name">旅行者</span>
        </div>

        <!-- 主标语 -->
        <div class="login-page__hero">
          <h1 class="login-page__hero-title">
            用 AI 重新定义<br>
            <span class="text-gradient">旅行规划</span>
          </h1>
          <p class="login-page__hero-desc">
            像跟朋友聊天一样，完成一次完整的旅行规划
          </p>
        </div>

        <!-- 目的地灵感网格（手账风格标签卡片） -->
        <div class="login-page__destinations">
          <div
            v-for="dest in destinations"
            :key="dest.name"
            class="login-page__dest-card"
            @click="goHome"
          >
            <div class="login-page__dest-img-wrapper">
              <img
                :src="dest.image"
                :alt="dest.name"
                class="login-page__dest-img"
                loading="lazy"
              >
              <div class="login-page__dest-overlay" />
            </div>
            <span class="login-page__dest-name">{{ dest.name }}</span>
          </div>
        </div>

        <!-- 功能亮点 -->
        <div class="login-page__features">
          <div
            v-for="feat in features"
            :key="feat.text"
            class="login-page__feat"
          >
            <IconTravel
              :name="feat.icon"
              :size="22"
              class="login-page__feat-icon"
            />
            <div class="login-page__feat-text">
              <span class="login-page__feat-title">{{ feat.text }}</span>
              <span class="login-page__feat-desc">{{ feat.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== 右侧：登录卡片 ===== -->
      <div class="login-page__card-wrapper">
        <div class="login-page__card">
          <LoginForm />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  width: 100%;
  min-height: 100vh;
  background: var(--gradient-hero);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6);
}

.login-page__deco {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.login-page__container {
  position: relative;
  z-index: 1;
  display: flex;
  gap: var(--space-10);
  max-width: 1100px;
  width: 100%;
  align-items: flex-start;
}

/* ===== 左侧品牌区 ===== */
.login-page__brand-section {
  flex: 1;
  min-width: 0;
  animation: fadeInLeft 0.8s var(--ease-out-expo);
}

@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

.login-page__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
}

.login-page__logo {
  color: var(--color-brand-500);
}

.login-page__brand-name {
  font-size: var(--text-h4);
  font-weight: 700;
  color: var(--color-brand-600);
}

/* Hero 文案 */
.login-page__hero {
  margin-bottom: var(--space-6);
}

.login-page__hero-title {
  font-size: clamp(28px, 4vw, 38px);
  font-weight: 800;
  line-height: 1.2;
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.login-page__hero-desc {
  font-size: var(--text-body);
  color: var(--color-text-tertiary);
  margin: 0;
  line-height: 1.5;
}

/* 目的地灵感网格 */
.login-page__destinations {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.login-page__dest-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s var(--ease-out-expo);
  box-shadow: 0 2px 12px rgba(139, 115, 85, 0.08);
}
.login-page__dest-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(139, 115, 85, 0.15);
}

.login-page__dest-img-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
}

.login-page__dest-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s var(--ease-out-expo);
}
.login-page__dest-card:hover .login-page__dest-img {
  transform: scale(1.08);
}

.login-page__dest-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(transparent 60%, rgba(44,44,44,0.4));
}

.login-page__dest-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: var(--space-2) var(--space-3);
  color: white;
  font-size: 13px;
  font-weight: 600;
  z-index: 1;
}

/* 功能亮点 */
.login-page__features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.login-page__feat {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-card);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.04);
  transition: all 0.2s;
}
.login-page__feat:hover {
  background: var(--color-brand-50);
}

.login-page__feat-icon {
  flex-shrink: 0;
  color: var(--color-brand-500);
}

.login-page__feat-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.login-page__feat-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.login-page__feat-desc {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

/* ===== 右侧登录卡 ===== */
.login-page__card-wrapper {
  flex-shrink: 0;
  width: 380px;
  animation: fadeInRight 0.8s var(--ease-out-expo);
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

.login-page__card {
  position: relative;
  padding: var(--space-8) var(--space-6);
  background: var(--color-glass-bg);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 40px rgba(139, 115, 85, 0.1);
  overflow: hidden;
}

/* 登录卡片内边距调整 */
.login-page__card {
  padding: var(--space-6) var(--space-5);
}

/* 响应式 */
@media (max-width: 900px) {
  .login-page__container {
    flex-direction: column;
    align-items: center;
  }
  .login-page__brand-section {
    max-width: 480px;
  }
  .login-page__card-wrapper {
    width: 100%;
    max-width: 420px;
  }
}

@media (max-width: 480px) {
  .login-page__destinations {
    grid-template-columns: repeat(3, 1fr);
  }
  .login-page__features {
    grid-template-columns: 1fr;
  }
}
</style>
