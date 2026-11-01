/**
 * V2.0 Trip Store — 行程执行状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  startTrip, getTrips, getTrip, updateTripStatus, getTripProgress,
  checkin, getCheckins, addExpense, getExpenses,
  detectAnomalies, getAdjustments, acceptAdjustment, rejectAdjustment,
  applyAdjustment, getReminder, advanceTripDay,
} from '@/api/trip'
import type { TripState, TripProgress, CheckinRecord, ExpenseRecord, AdjustmentRecord } from '@/api/trip'
import { getMockData } from '@/test/mocks/trip'

export const useTripStore = defineStore('trip', () => {
  /* ===== State ===== */
  const activeTrip = ref<TripState | null>(null)
  const trips = ref<TripState[]>([])
  const checkins = ref<CheckinRecord[]>([])
  const expenses = ref<ExpenseRecord[]>([])
  const adjustments = ref<AdjustmentRecord[]>([])
  const progress = ref<TripProgress | null>(null)
  const isLoading = ref(false)
  const reminder = ref<any>(null)
  const reminderLoading = ref(false)

  /* ===== Getters ===== */
  const isTripActive = computed(() => activeTrip.value?.status === 'active')
  const isTripPaused = computed(() => activeTrip.value?.status === 'paused')
  const progressPct = computed(() => progress.value?.progress_pct ?? 0)
  const todayCheckins = computed(() => {
    if (!activeTrip.value) return []
    const today = activeTrip.value.current_day
    return checkins.value.filter(c => {
      // 优先用 source_day 过滤，回落用 actual_at 日期推断
      if (c.source_day !== undefined && c.source_day !== null) {
        return c.source_day === today
      }
      if (c.actual_at) {
        const d = new Date(c.actual_at)
        return d.getDate() === new Date().getDate()
      }
      return false
    })
  })

  /* ===== Actions ===== */

  async function fetchTrips(status?: string) {
    const res = await getTrips({ status, page_size: 50 })
    trips.value = res.data.data?.list ?? []
  }

  async function beginTrip(planId: string, planData?: Record<string, unknown>) {
    const res = await startTrip(planId, planData)
    activeTrip.value = res.data.data ?? null
    return activeTrip.value
  }

  async function fetchTrip(tripId: string) {
    const res = await getTrip(tripId)
    activeTrip.value = res.data.data ?? null
    return activeTrip.value
  }

  async function changeStatus(status: string) {
    if (!activeTrip.value) return
    const res = await updateTripStatus(activeTrip.value.id, status)
    activeTrip.value = res.data.data ?? activeTrip.value
  }

  async function pauseTrip() { await changeStatus('paused') }
  async function resumeTrip() { await changeStatus('active') }
  async function completeTrip() { await changeStatus('completed') }

  async function fetchProgress(tripId?: string) {
    const id = tripId ?? activeTrip.value?.id
    if (!id) return
    const res = await getTripProgress(id)
    progress.value = res.data.data ?? null
  }

  // ---- Checkins ----

  async function doCheckin(data: {
    poi_type: string; poi_name: string; poi_id?: string
    source_day?: number
    lat?: number; lng?: number; photos?: any[]
    planned_at?: string; actual_at?: string
    planned_cost?: number; actual_cost?: number
    rating?: number; note?: string
  }) {
    if (!activeTrip.value) return
    const res = await checkin(activeTrip.value.id, data)
    const c = res.data.data
    if (c) checkins.value.unshift(c)
    await fetchProgress()  // refresh progress
    return c
  }

  async function fetchCheckins(day?: number) {
    if (!activeTrip.value) return
    const res = await getCheckins(activeTrip.value.id, { day, page_size: 200 })
    checkins.value = res.data.data?.list ?? []
  }

  // ---- Expenses ----

  async function doAddExpense(data: {
    category: string; amount: number
    planned_amount?: number; note?: string
    spent_at?: string; checkin_id?: string
  }) {
    if (!activeTrip.value) return
    const res = await addExpense(activeTrip.value.id, data)
    const e = res.data.data
    if (e) expenses.value.unshift(e)
    return e
  }

  async function fetchExpenses(category?: string) {
    if (!activeTrip.value) return
    const res = await getExpenses(activeTrip.value.id, category)
    expenses.value = res.data.data ?? []
  }

  // ---- Adjustments ----

  async function doDetectAnomalies(triggerType: string, detail?: Record<string, unknown>) {
    if (!activeTrip.value) return
    const res = await detectAnomalies(activeTrip.value.id, {
      trigger_type: triggerType,
      trigger_detail: detail,
    })
    return res.data.data
  }

  async function fetchAdjustments(status?: string) {
    if (!activeTrip.value) return
    const res = await getAdjustments(activeTrip.value.id, { status })
    adjustments.value = res.data.data?.list ?? []
  }

  async function doAcceptAdjustment(adjId: string) {
    if (!activeTrip.value) return
    const res = await acceptAdjustment(activeTrip.value.id, adjId)
    return res.data.data
  }

  async function doRejectAdjustment(adjId: string) {
    if (!activeTrip.value) return
    const res = await rejectAdjustment(activeTrip.value.id, adjId)
    return res.data.data
  }

  async function doApplyAdjustment(adjId: string) {
    if (!activeTrip.value) return
    const res = await applyAdjustment(activeTrip.value.id, adjId)
    return res.data.data
  }

  // ---- Mock / Test ----

  function loadTestTrip(scenario: 'normal' | 'over-budget' | 'completed' | 'empty' = 'normal') {
    const data = getMockData(scenario)
    activeTrip.value = data.trip
    checkins.value = data.checkins
    expenses.value = data.expenses
    adjustments.value = data.adjustments
    progress.value = data.progress
    reminder.value = {
      day: data.trip.current_day,
      reminder_text: '明天要去的龙井村和九溪烟树都在西湖景区附近，建议早上8点出发避开人流。今天龙井茶买得满意吗？明天还有机会感受九溪的清凉溪水！',
      first_stop: '龙井村',
      first_stop_time: '09:00',
      weather_advice: '晴，25-32°C，注意防晒',
      packing_hint: '充电宝、水杯、防晒霜、遮阳帽、墨镜',
    }
    return data.trip
  }

  // ---- Reminder ----

  async function doAdvanceDay() {
    if (!activeTrip.value) return
    const result = await advanceTripDay(activeTrip.value.id)
    activeTrip.value = result.data.data ?? activeTrip.value
    return activeTrip.value
  }

  async function fetchReminder() {
    if (!activeTrip.value) return
    reminderLoading.value = true
    reminder.value = null
    try {
      const res = await getReminder(activeTrip.value.id)
      reminder.value = res.data.data ?? null
      return reminder.value
    } finally {
      reminderLoading.value = false
    }
  }

  function clearReminder() {
    reminder.value = null
    reminderLoading.value = false
  }

  function clearTrip() {
    activeTrip.value = null
    checkins.value = []
    expenses.value = []
    adjustments.value = []
    progress.value = null
    clearReminder()
  }

  return {
    activeTrip, trips, checkins, expenses, adjustments, progress, isLoading, reminder,
    reminderLoading,
    isTripActive, isTripPaused, progressPct, todayCheckins,
    fetchTrips, beginTrip, fetchTrip, pauseTrip, resumeTrip, completeTrip,
    fetchProgress, doCheckin, fetchCheckins,
    doAddExpense, fetchExpenses,
    doDetectAnomalies, fetchAdjustments, doAcceptAdjustment, doRejectAdjustment, doApplyAdjustment,
    fetchReminder, clearReminder, clearTrip, doAdvanceDay,
    loadTestTrip,
  }
})
