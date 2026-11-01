/* ============================================================
   对话 API
   对应文档：API接口规范文档.md · §4 对话接口
   ============================================================ */

import http from './http'
import type { ApiResponse, PaginatedData, CursorData } from '@/types/api'
import type {
  Session,
  CreateSessionRequest,
  ConversationPlanRunRecord,
  Message,
  SendMessageRequest,
} from '@/types/chat'

/** 创建新会话 */
export function createSession(data?: CreateSessionRequest) {
  return http.post<ApiResponse<Session>>('/chat/sessions', data || {})
}

/** 获取会话列表 */
export function getSessions(params?: { page?: number; page_size?: number }) {
  return http.get<ApiResponse<PaginatedData<Session>>>('/chat/sessions', { params })
}

/** 删除会话 */
export function deleteSession(sessionId: string) {
  return http.delete<ApiResponse<Record<string, never>>>(`/chat/sessions/${sessionId}`)
}

/** 重命名会话 */
export function renameSession(sessionId: string, title: string) {
  return http.patch<ApiResponse<Session>>(`/chat/sessions/${sessionId}`, { title })
}

/** 置顶/取消置顶会话 */
export function togglePinSession(sessionId: string, pinned: boolean) {
  return http.patch<ApiResponse<Session>>(`/chat/sessions/${sessionId}`, { pinned })
}

/** 发送消息（返回 SSE 流，此函数仅触发请求，流的消费在 chatStore 中处理） */
export function sendMessage(sessionId: string, data: SendMessageRequest) {
  return http.post<ApiResponse<never>>(`/chat/sessions/${sessionId}/messages`, data, {
    // 不拦截 SSE 响应
    responseType: 'text',
  })
}

/** 获取 SSE 流 URL */
export function getStreamUrl(sessionId: string, lastEventId?: string): string {
  const base = `/api/v1/chat/sessions/${sessionId}/stream`
  return lastEventId ? `${base}?lastEventId=${lastEventId}` : base
}

/** 获取消息历史（分页） */
export function getMessages(
  sessionId: string,
  params?: { page?: number; page_size?: number },
) {
  return http.get<ApiResponse<PaginatedData<Message>>>(
    `/chat/sessions/${sessionId}/messages`,
    { params },
  )
}

/** 获取消息历史（游标翻页） */
export function getMessagesCursor(
  sessionId: string,
  params?: { before_id?: string; after_id?: string; limit?: number },
) {
  return http.get<ApiResponse<CursorData<Message>>>(
    `/chat/sessions/${sessionId}/messages`,
    { params },
  )
}

/** 获取会话内的全部方案运行记录 */
export function getSessionPlans(sessionId: string) {
  return http.get<ApiResponse<ConversationPlanRunRecord[]>>(
    `/chat/sessions/${sessionId}/plans`,
  )
}
