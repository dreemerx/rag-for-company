import apiClient from './client'

export interface Session {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export const chatApi = {
  // 对话管理
  getSessions: () =>
    apiClient.get<Session[]>('/chat/sessions'),

  createSession: (title: string = '新对话') =>
    apiClient.post<Session>('/chat/sessions', { title }),

  updateSession: (id: number, title: string) =>
    apiClient.patch<Session>(`/chat/sessions/${id}`, { title }),

  deleteSession: (id: number) =>
    apiClient.delete(`/chat/sessions/${id}`),

  // 消息历史
  getMessages: (sessionId: number) =>
    apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
}
