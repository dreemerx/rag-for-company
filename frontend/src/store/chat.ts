/**
 * 对话状态管理模块
 * - 使用 Zustand 管理对话列表和消息状态
 * - 支持对话创建、切换、删除、重命名
 * - 支持消息的添加和更新
 */
import { create } from 'zustand'
import { chatApi, Session } from '../api/chat'

/** 消息接口 */
interface Message {
  id: string                    // 消息 ID
  role: 'user' | 'assistant'   // 角色
  content: string               // 内容
  timestamp: Date               // 时间戳
}

/** 对话状态接口 */
interface ChatState {
  // 对话列表相关
  sessions: Session[]                     // 对话列表
  currentSessionId: number | null         // 当前选中的对话 ID
  loadingSessions: boolean                // 对话列表加载状态

  // 消息相关
  messages: Message[]                     // 当前对话的消息列表
  loading: boolean                        // 消息加载状态

  // 对话列表操作
  loadSessions: () => Promise<void>       // 加载对话列表
  createSession: () => Promise<number>    // 创建新对话
  switchSession: (sessionId: number) => Promise<void>  // 切换对话
  deleteSession: (sessionId: number) => Promise<void>  // 删除对话
  renameSession: (sessionId: number, title: string) => Promise<void>  // 重命名对话

  // 消息操作
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void  // 添加消息
  updateLastMessage: (content: string) => void  // 更新最后一条消息
  clearMessages: () => void               // 清空消息
  setLoading: (loading: boolean) => void  // 设置加载状态
}

/** 对话状态 Store */
export const useChatStore = create<ChatState>()((set, get) => ({
  sessions: [],
  currentSessionId: null,
  loadingSessions: false,
  messages: [],
  loading: false,

  // ==================== 对话列表 ====================

  /** 加载对话列表 */
  loadSessions: async () => {
    set({ loadingSessions: true })
    try {
      const { data } = await chatApi.getSessions()
      set({ sessions: data })
    } catch {
      // 静默失败
    } finally {
      set({ loadingSessions: false })
    }
  },

  /** 创建新对话 */
  createSession: async () => {
    const { data } = await chatApi.createSession()
    set((state) => ({
      sessions: [data, ...state.sessions],
      currentSessionId: data.id,
      messages: [],
    }))
    return data.id
  },

  /** 切换到指定对话 */
  switchSession: async (sessionId: number) => {
    set({ currentSessionId: sessionId, loading: true })
    try {
      const { data } = await chatApi.getMessages(sessionId)
      const messages: Message[] = data.map((m) => ({
        id: String(m.id),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at),
      }))
      set({ messages })
    } catch {
      set({ messages: [] })
    } finally {
      set({ loading: false })
    }
  },

  /** 删除对话 */
  deleteSession: async (sessionId: number) => {
    await chatApi.deleteSession(sessionId)
    const { currentSessionId } = get()
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== sessionId),
      ...(currentSessionId === sessionId
        ? { currentSessionId: null, messages: [] }
        : {}),
    }))
  },

  /** 重命名对话 */
  renameSession: async (sessionId: number, title: string) => {
    await chatApi.updateSession(sessionId, title)
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, title } : s
      ),
    }))
  },

  // ==================== 消息 ====================

  /** 添加消息 */
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: Date.now().toString(),
          timestamp: new Date(),
        },
      ],
    })),

  /** 更新最后一条消息（用于流式输出） */
  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages]
      if (messages.length > 0) {
        messages[messages.length - 1] = {
          ...messages[messages.length - 1],
          content,
        }
      }
      return { messages }
    }),

  /** 清空消息和当前对话 */
  clearMessages: () => set({ messages: [], currentSessionId: null }),

  /** 设置加载状态 */
  setLoading: (loading) => set({ loading }),
}))
