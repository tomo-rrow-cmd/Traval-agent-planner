/* ============================================================
   认证相关类型定义
   对应文档：API接口规范文档.md · §2-§3
   ============================================================ */

/** 发送短信验证码请求 */
export interface SmsCodeRequest {
  phone: string
}

/** 发送短信验证码响应 */
export interface SmsCodeResponse {
  expires_in: number
  retry_after: number
  need_captcha?: boolean
}

/** 手机号登录请求 */
export interface LoginRequest {
  method: 'phone' | 'password'
  phone: string
  code?: string
  password?: string
}

/** Token 刷新请求 */
export interface RefreshTokenRequest {
  refresh_token: string
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: UserProfile
}

/** Token 刷新响应 */
export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
}

/** 注册请求 */
export interface RegisterRequest {
  phone: string
  password: string
  nickname?: string
}

/** 注册响应 */
export interface RegisterResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: UserProfile
}

/** 用户资料 */
export interface UserProfile {
  id: string
  phone: string
  nickname: string
  avatar_url: string
  created_at: string
}

/** 更新用户资料请求 */
export interface UpdateProfileRequest {
  nickname?: string
  avatar_url?: string
}

/** 匿名数据合并请求 */
export interface MergeAnonymousRequest {
  anonymous_session_id: string
}

/** 匿名数据合并响应 */
export interface MergeAnonymousResponse {
  merged_session_count: number
  merged_plan_count: number
}

/** Token 结果（用于认证测试 mock） */
export interface TokenResult {
  access_token: string
  refresh_token: string
  expires_in: number
  user: UserProfile
}
