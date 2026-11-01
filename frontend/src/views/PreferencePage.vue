<script setup lang="ts">
import { onMounted } from 'vue'
import { usePreferenceStore } from '@/store/preferenceStore'
import type { TravelStyle, BudgetLevel, Pace, AgentPersonality } from '@/types/preference'

const prefStore = usePreferenceStore()

onMounted(() => { prefStore.fetchPreferences() })

const travelStyles: { value: TravelStyle; label: string; icon: string }[] = [
  { value: 'relaxed', label: '休闲放松', icon: '😌' },
  { value: 'balanced', label: '均衡适中', icon: '⚖️' },
  { value: 'intensive', label: '紧凑充实', icon: '🏃' },
  { value: 'food', label: '美食之旅', icon: '🍜' },
  { value: 'culture', label: '文化深度', icon: '🏛️' },
  { value: 'adventure', label: '探险刺激', icon: '🧗' },
]
const budgetLevels: { value: BudgetLevel; label: string }[] = [
  { value: 'budget', label: '经济实惠' }, { value: 'cost_effective', label: '性价比' },
  { value: 'quality', label: '品质享受' }, { value: 'luxury', label: '奢华体验' },
]
const paces: { value: Pace; label: string }[] = [
  { value: 'easy', label: '轻松' }, { value: 'moderate', label: '适中' }, { value: 'packed', label: '紧凑' },
]
const personalities: { value: AgentPersonality; label: string }[] = [
  { value: 'friendly', label: '友善' }, { value: 'professional', label: '专业' },
  { value: 'humorous', label: '幽默' }, { value: 'lively', label: '活泼' },
]
</script>

<template>
  <div class="preference-page">
    <div class="preference-page__header">
      <h2>偏好设置</h2>
      <p>定制您的旅行偏好，让 AI 更懂您</p>
    </div>

    <div class="preference-section">
      <h3 class="preference-section__title">
        🎯 旅行风格
      </h3>
      <div class="preference-grid">
        <div
          v-for="item in travelStyles"
          :key="item.value"
          class="preference-option"
          :class="{ 'preference-option--active': prefStore.effectivePreferences.travel_style === item.value }"
          @click="prefStore.saveWithDebounce({ travel_style: item.value })"
        >
          <span class="preference-option__icon">{{ item.icon }}</span>
          <span class="preference-option__label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="preference-section">
      <h3 class="preference-section__title">
        💰 预算等级
      </h3>
      <div class="preference-grid preference-grid--compact">
        <div
          v-for="item in budgetLevels"
          :key="item.value"
          class="preference-option"
          :class="{ 'preference-option--active': prefStore.effectivePreferences.budget_level === item.value }"
          @click="prefStore.saveWithDebounce({ budget_level: item.value })"
        >
          <span class="preference-option__label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="preference-section">
      <h3 class="preference-section__title">
        👣 行程节奏
      </h3>
      <div class="preference-grid preference-grid--compact">
        <div
          v-for="item in paces"
          :key="item.value"
          class="preference-option"
          :class="{ 'preference-option--active': prefStore.effectivePreferences.pace === item.value }"
          @click="prefStore.saveWithDebounce({ pace: item.value })"
        >
          <span class="preference-option__label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="preference-section">
      <h3 class="preference-section__title">
        🤖 AI 助手性格
      </h3>
      <div class="preference-grid preference-grid--compact">
        <div
          v-for="item in personalities"
          :key="item.value"
          class="preference-option"
          :class="{ 'preference-option--active': prefStore.effectivePreferences.agent_personality === item.value }"
          @click="prefStore.saveWithDebounce({ agent_personality: item.value })"
        >
          <span class="preference-option__label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <div class="preference-section">
      <h3 class="preference-section__title">
        🤖 AI 助手名称
      </h3>
      <a-input
        :value="prefStore.effectivePreferences.custom_agent_name"
        placeholder="给您的 AI 助手取个名字"
        style="max-width: 300px;"
        @change="(e: any) => prefStore.saveWithDebounce({ custom_agent_name: e.target.value }, 800)"
      />
    </div>

    <div
      v-if="prefStore.saveStatus === 'success'"
      class="preference-save-status"
    >
      <span class="preference-saved-badge">✓ 偏好已保存</span>
    </div>
  </div>
</template>

<style scoped>
.preference-page { max-width: 640px; margin: 0 auto; padding: var(--space-6) 0; }
.preference-page__header { margin-bottom: var(--space-8); }
.preference-page__header h2 { font-size: var(--text-h2); font-weight: var(--fw-bold); margin-bottom: var(--space-1); }
.preference-page__header p { color: var(--color-text-tertiary); }
.preference-section { margin-bottom: var(--space-8); }
.preference-section__title { font-size: var(--text-body); font-weight: var(--fw-semibold); margin-bottom: var(--space-4); }
.preference-grid { display: flex; flex-wrap: wrap; gap: var(--space-3); }
.preference-grid--compact { gap: var(--space-2); }
.preference-option {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-3) var(--space-4); background: var(--color-bg-card);
  border: 1px solid var(--color-border); border-radius: var(--radius-sm);
  cursor: pointer; transition: all var(--dur-fast); user-select: none;
}
.preference-option:hover { border-color: var(--color-brand-300); background: var(--color-brand-50); }
.preference-option--active { border-color: var(--color-brand-500); background: var(--color-brand-50); color: var(--color-brand-700); font-weight: var(--fw-medium); }
.preference-option__icon { font-size: 18px; }
.preference-option__label { font-size: var(--text-body-sm); }
.preference-save-status { text-align: center; padding: var(--space-4); }
.preference-saved-badge { font-size: var(--text-body-sm); color: var(--color-success); font-weight: var(--fw-medium); }
</style>
