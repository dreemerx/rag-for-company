import apiClient from './client'

export interface ChatRequest {
  message: string
  session_id?: string
}

export interface ChatResponse {
  reply: string
  session_id: string
  remaining_quota: {
    remaining_requests: number
    remaining_tokens: number
    max_requests_per_minute: number
    max_tokens_per_session: number
  }
}

export interface Session {
  session_id: string
  created_at: string
  last_active: string
  message_count: number
}

export const chatApi = {
  sendMessage: (data: ChatRequest) =>
    apiClient.post<ChatResponse>('/chat/send', data),

  getSessions: () =>
    apiClient.get<Session[]>('/chat/sessions'),

  deleteSession: (sessionId: string) =>
    apiClient.delete(`/chat/sessions/${sessionId}`),
}
