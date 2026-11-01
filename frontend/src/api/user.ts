/* ============================================================
   用户 API
   对应文档：API接口规范文档.md · §3 用户接口
   ============================================================ */

import http from './http'
import type { ApiResponse } from '@/types/api'
import type {
  UserProfile,
  UpdateProfileRequest,
  MergeAnonymousRequest,
  MergeAnonymousResponse,
} from '@/types/auth'
import type { UserPreferences } from '@/types/preference'

/** 获取用户资料 */
export function getUserProfile() {
  return http.get<ApiResponse<UserProfile>>('/user/profile')
}

/** 更新用户资料 */
export function updateUserProfile(data: UpdateProfileRequest) {
  return http.put<ApiResponse<UserProfile>>('/user/profile', data)
}

/** 获取偏好配置 */
export function getUserPreferences() {
  return http.get<ApiResponse<UserPreferences>>('/user/preferences')
}

/** 更新偏好配置 */
export function updateUserPreferences(data: Partial<UserPreferences>) {
  return http.put<ApiResponse<UserPreferences>>('/user/preferences', data)
}

/** 合并匿名数据 */
export function mergeAnonymousData(data: MergeAnonymousRequest) {
  return http.post<ApiResponse<MergeAnonymousResponse>>('/user/sessions/anonymous/merge', data)
}
