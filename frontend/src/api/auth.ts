/* ============================================================
   认证 API
   对应文档：API接口规范文档.md · §2 认证接口
   ============================================================ */

import http from './http'
import type { ApiResponse } from '@/types/api'
import type {
  SmsCodeRequest,
  SmsCodeResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  RegisterRequest,
  RegisterResponse,
} from '@/types/auth'

/** 发送短信验证码 */
export function sendSmsCode(data: SmsCodeRequest) {
  return http.post<ApiResponse<SmsCodeResponse>>('/auth/sms-codes', data)
}

/** 手机号验证码登录 */
export function loginWithPhone(data: LoginRequest) {
  return http.post<ApiResponse<LoginResponse>>('/auth/sessions', data)
}

/** 登录（别名，供测试导入） */
export { loginWithPhone as login }

/** 注册 */
export function register(data: RegisterRequest) {
  return http.post<ApiResponse<RegisterResponse>>('/auth/register', data)
}

/** 刷新 Token */
export function refreshToken(data: RefreshTokenRequest) {
  return http.post<ApiResponse<RefreshTokenResponse>>('/auth/tokens', data)
}

/** 登出 */
export function logout() {
  return http.delete<ApiResponse<Record<string, never>>>('/auth/sessions/current')
}
