/* ============================================================
   HTTP 客户端 — Axios 实例与拦截器
   对应文档：API接口规范文档.md · §1 通用约定
   ============================================================ */

import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import type { ApiResponse } from '@/types/api'

const BASE_URL = '/api/v1'

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
  },
})

/* ========== 请求拦截器 ========== */
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 注入 Access Token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 匿名会话标识
    const sessionId = localStorage.getItem('anonymous_session_id')
    if (sessionId && !token) {
      config.headers['X-Session-Id'] = sessionId
    }

    return config
  },
  (error) => Promise.reject(error),
)

/* ========== 响应拦截器 ========== */
http.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    // Blob / ArrayBuffer 响应（文件下载）跳过业务码检查
    const respType = response.config.responseType
    if (respType === 'blob' || respType === 'arraybuffer') {
      return response
    }
    const { data } = response
    // 业务错误码非 0 也 reject
    if (data.code !== 0) {
      return Promise.reject(new ApiError(data.code, data.message, data.request_id ?? ''))
    }
    return response
  },
  async (error) => {
    if (error.response?.status === 401) {
      // Token 过期，尝试刷新
      const refreshed = await tryRefreshToken()
      if (refreshed) {
        // 重试原始请求
        const config = error.config
        config.headers.Authorization = `Bearer ${localStorage.getItem('access_token')}`
        return http(config)
      }
      // 刷新失败，清除登录态并跳转首页
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('expires_at')
      window.location.href = '/'
    }
    return Promise.reject(error)
  },
)

/* ========== Token 刷新逻辑 ========== */
async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return false

  try {
    const res = await axios.post(`${BASE_URL}/auth/tokens`, {
      refresh_token: refreshToken,
    })
    const { access_token, refresh_token } = res.data.data
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    return true
  } catch {
    return false
  }
}

/* ========== 自定义 API 错误类 ========== */
export class ApiError extends Error {
  code: number
  requestId: string

  constructor(code: number, message: string, requestId: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.requestId = requestId
  }
}

export default http
