/**
 * V2.0 Trip API — 行程执行 / 签到 / 花费 / 调整
 */

import http from './http'
import type { ApiResponse, PaginatedData } from '@/types/api'

export interface TripState {
  id: string
  plan_id: string
  user_id: string
  status: 'active' | 'paused' | 'completed' | 'abandoned'
  current_day: number
  total_pois: number
  checked_in: number
  started_at: string | null
  paused_at: string | null
  completed_at: string | null
  last_lat: number | null
  last_lng: number | null
  budget_total: number | null
  budget_spent: number
  budget_remain: number | null
  created_at: string
  updated_at: string
}

export interface TripProgress {
  trip_id: string
  status: string
  current_day: number
  progress_pct: number
  checked_in: number
  total_pois: number
  budget_total: number
  budget_spent: number
  budget_remain: number
  time_delta_total_min: number
  last_location: { lat: number; lng: number } | null
}

export interface CheckinRecord {
  id: string
  trip_id: string
  poi_type: string
  poi_name: string
  poi_id?: string
  source_day?: number
  lat?: number
  lng?: number
  photos: PhotoMeta[]
  planned_at?: string | null
  actual_at?: string | null
  time_delta_min: number
  planned_cost?: number | null
  actual_cost?: number | null
  rating?: number | null
  note?: string | null
  created_at: string
}

export interface PhotoMeta {
  url: string
  thumbnail_url?: string
  ai_caption?: string
  ai_tags?: string[]
  quality_score?: number
  caption?: string
  is_portrait?: boolean
}

export interface ExpenseRecord {
  id: string
  trip_id: string
  checkin_id?: string | null
  category: string
  amount: number
  planned_amount?: number
  note?: string | null
  spent_at?: string | null
}

export interface AdjustmentRecord {
  id: string
  trip_id: string
  trigger_type: string
  trigger_detail?: Record<string, unknown>
  original_plan?: unknown
  adjusted_plan?: unknown
  reason?: string
  status: 'pending' | 'accepted' | 'rejected' | 'applied'
  accepted_at?: string
  created_at: string
}

// ---- Trip CRUD ----

export function startTrip(planId: string, planData?: Record<string, unknown>) {
  const body: Record<string, unknown> = { plan_id: planId }
  if (planData) body.plan_data = planData
  return http.post<ApiResponse<TripState>>('/trips', body)
}

export function getTrips(params?: { status?: string; page?: number; page_size?: number }) {
  return http.get<ApiResponse<PaginatedData<TripState>>>('/trips', { params })
}

export function getTrip(tripId: string) {
  return http.get<ApiResponse<TripState>>(`/trips/${tripId}`)
}

export function updateTripStatus(tripId: string, status: string) {
  return http.patch<ApiResponse<TripState>>(`/trips/${tripId}`, { status })
}

export function getTripProgress(tripId: string) {
  return http.get<ApiResponse<TripProgress>>(`/trips/${tripId}/progress`)
}

// ---- Checkins ----

export function checkin(tripId: string, data: {
  poi_type: string
  poi_name: string
  poi_id?: string
  source_day?: number
  lat?: number
  lng?: number
  photos?: PhotoMeta[]
  planned_at?: string
  actual_at?: string
  planned_cost?: number
  actual_cost?: number
  rating?: number
  note?: string
}) {
  return http.post<ApiResponse<CheckinRecord>>(`/trips/${tripId}/checkins`, data)
}

export function getCheckins(tripId: string, params?: { day?: number; page?: number; page_size?: number }) {
  return http.get<ApiResponse<PaginatedData<CheckinRecord>>>(`/trips/${tripId}/checkins`, { params })
}

// ---- Expenses ----

export function addExpense(tripId: string, data: {
  category: string
  amount: number
  planned_amount?: number
  note?: string
  spent_at?: string
  checkin_id?: string
}) {
  return http.post<ApiResponse<ExpenseRecord>>(`/trips/${tripId}/expenses`, data)
}

export function getExpenses(tripId: string, category?: string) {
  return http.get<ApiResponse<ExpenseRecord[]>>(`/trips/${tripId}/expenses`, { params: { category } })
}

// ---- Adjustments ----

export function detectAnomalies(tripId: string, data: {
  trigger_type: string
  trigger_detail?: Record<string, unknown>
  daily_plan?: unknown[]
  preferences?: string[]
  destination?: string
}) {
  return http.post<ApiResponse<AdjustmentRecord>>(`/trips/${tripId}/adjustments/detect`, data)
}

export function getAdjustments(tripId: string, params?: { status?: string; page?: number; page_size?: number }) {
  return http.get<ApiResponse<PaginatedData<AdjustmentRecord>>>(`/trips/${tripId}/adjustments`, { params })
}

export function acceptAdjustment(tripId: string, adjId: string) {
  return http.post<ApiResponse<AdjustmentRecord>>(`/trips/${tripId}/adjustments/${adjId}/accept`)
}

export function rejectAdjustment(tripId: string, adjId: string) {
  return http.post<ApiResponse<AdjustmentRecord>>(`/trips/${tripId}/adjustments/${adjId}/reject`)
}

export function applyAdjustment(tripId: string, adjId: string) {
  return http.post<ApiResponse<AdjustmentRecord>>(`/trips/${tripId}/adjustments/${adjId}/apply`)
}

// ---- Day Advancement ----

export function advanceTripDay(tripId: string) {
  return http.post<ApiResponse<TripState>>(`/trips/${tripId}/advance-day`)
}

// ---- Reminders ----

export function getReminder(tripId: string) {
  return http.get<ApiResponse<Record<string, unknown>>>(`/trips/${tripId}/reminder`)
}

// ---- Photos ----

export function annotatePhotos(tripId: string, checkin: Record<string, unknown>) {
  return http.post<ApiResponse<Record<string, unknown>>>(`/trips/${tripId}/photos/annotate`, { checkin })
}
