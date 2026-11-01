/* ============================================================
   API 通用类型定义
   对应文档：API接口规范文档.md · §1
   ============================================================ */

/** 统一 API 响应格式 */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T | null
  request_id?: string
}

/** 分页请求参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

/** 分页响应数据 */
export interface PaginatedData<T> {
  list: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** 游标翻页请求参数 */
export interface CursorParams {
  before_id?: string
  after_id?: string
  limit?: number
}

/** 游标翻页响应数据 */
export interface CursorData<T> {
  list: T[]
  has_more: boolean
  next_before_id?: string
}

/** API 错误码 */
export const ErrorCode = {
  SUCCESS: 10000,
  BAD_REQUEST: 10001,
  MISSING_PARAM: 10002,
  NOT_FOUND: 10003,
  RATE_LIMITED: 10004,
  UNAUTHORIZED: 20001,
  TOKEN_INVALID: 20002,
  TOKEN_EXPIRED: 20003,
  FORBIDDEN: 20004,
} as const

export type ErrorCode = (typeof ErrorCode)[keyof typeof ErrorCode]
