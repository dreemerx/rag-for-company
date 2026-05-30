import { create } from 'zustand'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  loading: boolean
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void
  setSessionId: (sessionId: string) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  sessionId: null,
  loading: false,

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

  setSessionId: (sessionId) => set({ sessionId }),

  setLoading: (loading) => set({ loading }),

  clearMessages: () => set({ messages: [], sessionId: null }),
}))
