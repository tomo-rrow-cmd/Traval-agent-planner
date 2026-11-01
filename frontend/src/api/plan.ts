/* ============================================================
   方案 API
   对应文档：API接口规范文档.md · §5 方案接口
   ============================================================ */

import http from './http'
import type { ApiResponse, PaginatedData } from '@/types/api'
import type {
  PlanSummary,
  PlanDetail,
  PlanListParams,
  GeneratePlanRequest,
  ModifyPlanRequest,
  RegeneratePlanRequest,
  ExportTaskResponse,
  ExportFormat,
  PlanFromDataRequest,
  ShareOptions,
  ShareResult,
} from '@/types/plan'

/** 获取方案列表 */
export function getPlans(params?: PlanListParams) {
  return http.get<ApiResponse<PaginatedData<PlanSummary>>>('/plans', { params })
}

/** 触发方案生成（返回 SSE 流） */
export function generatePlan(data: GeneratePlanRequest) {
  return http.post<ApiResponse<never>>('/plans', data, { responseType: 'text' })
}

/** 获取方案详情 */
export function getPlanDetail(planId: string) {
  return http.get<ApiResponse<PlanDetail>>(`/plans/${planId}`)
}

/** 局部修改方案（返回 SSE 流） */
export function modifyPlan(planId: string, data: ModifyPlanRequest) {
  return http.patch<ApiResponse<never>>(`/plans/${planId}`, data, { responseType: 'text' })
}

/** 重新生成方案（返回 SSE 流） */
export function regeneratePlan(planId: string, data: RegeneratePlanRequest) {
  return http.post<ApiResponse<never>>(`/plans/${planId}/generations`, data, { responseType: 'text' })
}

/** 删除方案 */
export function deletePlan(planId: string) {
  return http.delete<ApiResponse<Record<string, never>>>(`/plans/${planId}`)
}

/** 从本地数据创建方案（保存未持久化的方案到后端） */
export function createPlanFromData(data: PlanFromDataRequest) {
  return http.post<ApiResponse<PlanDetail>>('/plans/from-data', data)
}

/** 导出方案 */
export function exportPlan(planId: string, format: ExportFormat) {
  return http.post<ApiResponse<ExportTaskResponse>>(
    `/plans/${planId}/exports`,
    null,
    { params: { format } },
  )
}

/** 查询导出任务状态 */
export function getExportTaskStatus(taskId: string) {
  return http.get<ApiResponse<{
    task_id: string
    status: 'processing' | 'completed' | 'failed'
    progress: number
    message: string
    download_url?: string
    expires_at?: string
    error?: { code: number; message: string }
  }>>(`/tasks/${taskId}`)
}

/** 下载导出文件（直接返回 Blob） */
export function downloadExport(taskId: string) {
  return http.get<Blob>(`/tasks/${taskId}/download`, { responseType: 'blob' })
}

/** 分享方案 */
export function sharePlan(planId: string, options?: ShareOptions) {
  return http.post<ApiResponse<ShareResult>>(`/plans/${planId}/shares`, options || {})
}

/** 收藏/取消收藏 */
export function toggleFavorite(planId: string) {
  return http.post<ApiResponse<{ is_favorite: boolean }>>(`/plans/${planId}/favorites`)
}
