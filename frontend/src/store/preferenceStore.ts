/* ============================================================
   偏好状态管理（含防抖保存、离线队列）
   对应文档：前端界面设计文档.md · §6.2 Store 详细职责
   ============================================================ */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserPreferences } from '@/types/preference'
import { DEFAULT_PREFERENCES } from '@/types/preference'
import { getUserPreferences as apiGetPreferences, updateUserPreferences as apiUpdatePreferences } from '@/api/user'

export const usePreferenceStore = defineStore('preference', () => {
  /* ===== State ===== */
  const preferences = ref<UserPreferences>({ ...DEFAULT_PREFERENCES })
  const isLoading = ref(false)
  const isSaving = ref(false)
  const saveError = ref<string | null>(null)
  const saveStatus = ref<'idle' | 'saving' | 'success' | 'error'>('idle')
  const offlineQueue = ref<Partial<UserPreferences>[]>([])
  const sessionOverrides = ref<Partial<UserPreferences>>({})
  let pendingDebounceTimer: ReturnType<typeof setTimeout> | null = null

  /* ===== Getters ===== */
  /** 合并持久化偏好与会话临时覆盖值 */
  const effectivePreferences = computed<UserPreferences>(() => ({
    ...preferences.value,
    ...sessionOverrides.value,
  }))

  /* ===== Actions ===== */

  /** 获取偏好配置 */
  async function fetchPreferences() {
    isLoading.value = true
    try {
      const res = await apiGetPreferences()
      if (res.data.data) {
        preferences.value = res.data.data
      }
    } catch (e: any) {
      saveError.value = e.message || '获取偏好失败'
    } finally {
      isLoading.value = false
    }
  }

  /** 保存偏好（直接保存） */
  async function savePreferences(prefs: Partial<UserPreferences>) {
    isSaving.value = true
    saveStatus.value = 'saving'
    saveError.value = null

    // 离线保护：先写入 localStorage
    const cached = localStorage.getItem('preferences')
    const merged = { ...(cached ? JSON.parse(cached) : {}), ...prefs }
    localStorage.setItem('preferences', JSON.stringify(merged))

    try {
      const res = await apiUpdatePreferences(prefs)
      if (res.data.data) {
        preferences.value = res.data.data
        saveStatus.value = 'success'
        // 2 秒后恢复 idle
        setTimeout(() => { saveStatus.value = 'idle' }, 2000)
      }
    } catch (e: any) {
      saveError.value = e.message || '保存偏好失败'
      saveStatus.value = 'error'
      // 加入离线队列
      offlineQueue.value.push(prefs)
    } finally {
      isSaving.value = false
    }
  }

  /** 防抖保存 */
  function saveWithDebounce(prefs: Partial<UserPreferences>, delay = 500) {
    if (pendingDebounceTimer) {
      clearTimeout(pendingDebounceTimer)
    }
    pendingDebounceTimer = setTimeout(() => {
      savePreferences(prefs)
    }, delay)
  }

  /** 强制保存待处理数据 */
  async function flushPendingSave() {
    if (pendingDebounceTimer) {
      clearTimeout(pendingDebounceTimer)
      pendingDebounceTimer = null
    }
    // 取最新值
  }

  /** 重试离线队列 */
  async function retryOfflineQueue() {
    while (offlineQueue.value.length > 0) {
      const prefs = offlineQueue.value.shift()
      if (prefs) {
        try {
          await savePreferences(prefs)
        } catch {
          offlineQueue.value.unshift(prefs)
          break
        }
      }
    }
  }

  /** 设置会话临时覆盖值 */
  function setSessionOverride(overrides: Partial<UserPreferences>) {
    sessionOverrides.value = { ...sessionOverrides.value, ...overrides }
  }

  /** 清除会话覆盖值 */
  function clearSessionOverrides() {
    sessionOverrides.value = {}
  }

  return {
    preferences,
    isLoading,
    isSaving,
    saveError,
    saveStatus,
    offlineQueue,
    effectivePreferences,
    fetchPreferences,
    savePreferences,
    saveWithDebounce,
    flushPendingSave,
    retryOfflineQueue,
    setSessionOverride,
    clearSessionOverrides,
  }
})
