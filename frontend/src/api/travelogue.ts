/**
 * V2.0 Travelogue API — 游记 / 社交素材 / 分享
 */

import http from './http'
import type { ApiResponse, PaginatedData } from '@/types/api'

export interface TravelogueData {
  id: string
  trip_id: string
  user_id: string
  title: string | null
  content: string | null
  cover_url: string | null
  style?: 'diary' | 'xiaohongshu' | 'guide'
  photos: string[]
  total_days: number | null
  total_pois: number | null
  total_cost: number | null
  total_photos: number
  status: 'draft' | 'published' | 'shared'
  created_at: string
  updated_at: string
}

export interface SocialMaterial {
  id: string
  trip_id: string
  user_id: string
  type: 'moment_9grid' | 'single_card' | 'day_summary' | 'collage' | 'trip_highlight' | 'budget_card'
  title: string | null
  content: string | null
  hashtags: string[]
  location_tag: string | null
  images: MaterialImage[]
  layout: string | null
  overlay_data: Record<string, unknown> | null
  source_day: number | null
  source_poi: string | null
  is_generated: boolean
  is_favorite: boolean
  used_in_travelogue: boolean
  created_at: string
}

export interface MaterialImage {
  url: string
  caption?: string
  order: number
  is_cover?: boolean
}

export interface ShareData {
  id: string
  user_id: string
  target_type: string
  target_id: string
  share_code: string
  has_password: boolean
  expire_at: string | null
  view_count: number
  share_url: string
}

// ---- Travelogues ----

export function generateTravelogue(
  tripId: string,
  style: string = 'diary',
  regenerate: boolean = false,
) {
  return http.post<ApiResponse<TravelogueData>>('/travelogues', {
    trip_id: tripId,
    style,
    regenerate,
  })
}

export function getTravelogues(params?: { status?: string; page?: number; page_size?: number }) {
  return http.get<ApiResponse<PaginatedData<TravelogueData>>>('/travelogues', { params })
}

export function getTravelogue(id: string) {
  return http.get<ApiResponse<TravelogueData>>(`/travelogues/${id}`)
}

export function getTravelogueByTrip(tripId: string) {
  return http.get<ApiResponse<TravelogueData | null>>(`/travelogues/by-trip/${tripId}`)
}

export function updateTravelogue(id: string, data: Partial<TravelogueData>) {
  return http.patch<ApiResponse<TravelogueData>>(`/travelogues/${id}`, data)
}

export function publishTravelogue(id: string) {
  return http.post<ApiResponse<TravelogueData>>(`/travelogues/${id}/publish`)
}

// ---- Social Materials ----

export function generateMaterials(tripId: string) {
  return http.post<ApiResponse<{ materials: SocialMaterial[] }>>('/travelogues/materials/generate', { trip_id: tripId })
}

export function getMaterials(tripId: string, type?: string) {
  return http.get<ApiResponse<SocialMaterial[]>>('/travelogues/materials', { params: { trip_id: tripId, type } })
}

export function favoriteMaterial(materialId: string, isFavorite: boolean = true) {
  return http.post<ApiResponse<SocialMaterial>>(`/travelogues/materials/${materialId}/favorite`, { is_favorite: isFavorite })
}

// ---- Shares ----

export function createShare(data: { target_type: string; target_id: string; password?: string; expire_hours?: number }) {
  return http.post<ApiResponse<ShareData>>('/travelogues/shares', data)
}

export function getShareByCode(code: string) {
  return http.get<ApiResponse<ShareData>>(`/travelogues/shares/${code}`)
}

export function deleteTravelogue(id: string) {
  return http.delete<ApiResponse<null>>(`/travelogues/${id}`)
}
