/**
 * 对话 API 模块
 * - 封装对话相关的 API 调用
 * - 包括对话管理和消息历史查询
 */
import apiClient from './client'

/** 对话会话接口 */
export interface Session {
  id: number                    // 会话 ID
  title: string                 // 会话标题
  created_at: string            // 创建时间
  updated_at: string            // 更新时间
  message_count: number         // 消息数量
}

/** 聊天消息接口 */
export interface ChatMessage {
  id: number                    // 消息 ID
  role: 'user' | 'assistant'   // 角色（用户或助手）
  content: string               // 消息内容
  created_at: string            // 创建时间
}

/** 对话 API */
export const chatApi = {
  /** 获取对话列表 */
  getSessions: () =>
    apiClient.get<Session[]>('/chat/sessions'),

  /** 创建新对话 */
  createSession: (title: string = '新对话') =>
    apiClient.post<Session>('/chat/sessions', { title }),

  /** 更新对话标题 */
  updateSession: (id: number, title: string) =>
    apiClient.patch<Session>(`/chat/sessions/${id}`, { title }),

  /** 删除对话 */
  deleteSession: (id: number) =>
    apiClient.delete(`/chat/sessions/${id}`),

  /** 获取对话消息历史 */
  getMessages: (sessionId: number) =>
    apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
}
