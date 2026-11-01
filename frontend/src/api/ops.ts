// ============================================================
// 运维（健康检查 / 任务状态轮询）API
// ============================================================

import http from './http'
import type { ApiResponse } from '@/types/api'
import type { HealthData, TaskStatus } from '@/types/common'

/** 健康检查 */
export function healthCheck(): Promise<ApiResponse<HealthData>> {
  return http.get<ApiResponse<HealthData>>('/health').then((r) => r.data)
}

/** 查询异步任务状态 */
export function getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
  return http.get<ApiResponse<TaskStatus>>(`/tasks/${taskId}`).then((r) => r.data)
}
