// ============================================================
// 对话类型 — 对齐后端 app/schemas/chat.py + agent SSE events
// ============================================================

export type SessionStatus = 'active' | 'archived' | 'deleted'
export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageType = 'text' | 'question' | 'plan_progress' | 'plan_result'

export interface ChatSession {
  id: string
  title: string
  status: SessionStatus
  message_count: number
  pinned: boolean
  plan_run_id?: string
  last_message_preview?: string
  created_at: string
  updated_at: string
}

export interface ChatSessionCreateRequest {
  title?: string
}

export interface ChatMessageCreateRequest {
  content: string
}

export interface MessageRecord {
  id: string
  session_id: string
  role: MessageRole
  content: string
  message_type: MessageType
  metadata?: Record<string, unknown>
  created_at: string
}

export interface ConversationPlanRunRecord {
  id: string
  destination: string
  days: number
  summary: Record<string, any>
  created_at: string
}

// ---- SSE 事件类型 ----

export type SSEEventType = 'step_start' | 'message' | 'message_delta' | 'progress' | 'step_end' | 'error' | 'done'

export interface SSEStepStartData {
  step: string
  label: string
}

export interface SSEMessageData {
  role: 'assistant'
  content: string
  message_type: MessageType
  suggestions?: string[]
}

export interface SSEMessageDeltaData {
  role: 'assistant'
  content_delta: string
  message_type: MessageType
  sequence: number
}

export interface SSEProgressData {
  percent: number
  message: string
}

export interface SSEStepEndData {
  step: string
}

export interface SSEErrorData {
  message: string
}

export interface SSEDoneData {
  plan_id: string
  redirect_url: string
  session_id: string
  result_message?: string
  result_format?: 'compact_v1'
  summary?: {
    destination: string
    days: number
    daily_plan: any[]
    meal_plan: any[]
    hotel_plan: any
    traffic: any
    budget: any
    souvenirs: any[]
  }
  content_blocks?: any[]
}

export type SSEEventData =
  | ({ event: 'step_start' } & SSEStepStartData)
  | ({ event: 'message' } & SSEMessageData)
  | ({ event: 'message_delta' } & SSEMessageDeltaData)
  | ({ event: 'progress' } & SSEProgressData)
  | ({ event: 'step_end' } & SSEStepEndData)
  | ({ event: 'error' } & SSEErrorData)
  | ({ event: 'done' } & SSEDoneData)

// ---- 别名（兼容旧引用） ----

export type Session = ChatSession
export type CreateSessionRequest = ChatSessionCreateRequest
export type Message = MessageRecord
export type SendMessageRequest = ChatMessageCreateRequest
