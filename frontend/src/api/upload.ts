/* ============================================================
   图片上传 API
   ============================================================ */

import type { AxiosResponse } from 'axios'
import http from './http'
import type { ApiResponse } from '@/types/api'

export interface UploadResult {
  url: string
  filename: string
}

/** 上传图片文件 → 返回可访问的 URL */
export function uploadImage(file: File): Promise<AxiosResponse<ApiResponse<UploadResult>>> {
  const form = new FormData()
  form.append('file', file)
  return http.post('/chat/upload/image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000, // 上传超时 60s
  })
}
