import type { ApiResponse } from '@/types/api'
import type { TokenResult, UserProfile } from '@/types/auth'

export const mockUser: UserProfile = {
  id: 'usr_mock001',
  phone: '138****5678',
  nickname: '旅行者Mock',
  avatar_url: '',
  created_at: '2026-06-01T08:00:00Z',
}

export const mockToken: TokenResult = {
  access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_access_token',
  refresh_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_refresh_token',
  expires_in: 3600,
  user: mockUser,
}

export const mockRegisterResponse: ApiResponse<TokenResult> = {
  code: 0,
  message: '注册成功',
  data: mockToken,
}

export const mockLoginResponse: ApiResponse<TokenResult> = {
  code: 0,
  message: '登录成功',
  data: mockToken,
}

export const mockSmsCodeResponse: ApiResponse<{ expires_in: number; retry_after: number }> = {
  code: 0,
  message: '验证码已发送',
  data: { expires_in: 300, retry_after: 60 },
}

export const mockRefreshTokenResponse: ApiResponse<TokenResult> = {
  code: 0,
  message: 'Token 已刷新',
  data: {
    ...mockToken,
    access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_refreshed_token',
  },
}

export const mockAnonymousMergeResponse: ApiResponse<{ merged_session_count: number; merged_plan_count: number }> = {
  code: 0,
  message: '合并完成',
  data: { merged_session_count: 3, merged_plan_count: 0 },
}
