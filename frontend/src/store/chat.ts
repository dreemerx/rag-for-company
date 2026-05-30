import { create } from 'zustand'
import { chatApi, Session } from '../api/chat'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ChatState {
  // 对话列表
  sessions: Session[]
  currentSessionId: number | null
  loadingSessions: boolean

  // 消息
  messages: Message[]
  loading: boolean

  // 对话列表操作
  loadSessions: () => Promise<void>
  createSession: () => Promise<number>
  switchSession: (sessionId: number) => Promise<void>
  deleteSession: (sessionId: number) => Promise<void>
  renameSession: (sessionId: number, title: string) => Promise<void>

  // 消息操作
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  updateLastMessage: (content: string) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessions: [],
  currentSessionId: null,
  loadingSessions: false,
  messages: [],
  loading: false,

  // ==================== 对话列表 ====================

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

  createSession: async () => {
    const { data } = await chatApi.createSession()
    set((state) => ({
      sessions: [data, ...state.sessions],
      currentSessionId: data.id,
      messages: [],
    }))
    return data.id
  },

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

  renameSession: async (sessionId: number, title: string) => {
    await chatApi.updateSession(sessionId, title)
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, title } : s
      ),
    }))
  },

  // ==================== 消息 ====================

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

  clearMessages: () => set({ messages: [], currentSessionId: null }),

  setLoading: (loading) => set({ loading }),
}))
