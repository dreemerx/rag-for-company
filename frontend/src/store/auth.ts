import { create } from 'zustand'

interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  department: string | null
  roles: string[]
}

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean
  setAuth: (token: string, refreshToken: string, user: User) => void
  logout: () => void
  updateUser: (user: User) => void
}

// 从 localStorage 读取初始状态
function loadAuth(): Partial<AuthState> {
  try {
    const stored = localStorage.getItem('auth-storage')
    if (stored) {
      const parsed = JSON.parse(stored)
      if (parsed?.state?.token && parsed?.state?.isAuthenticated) {
        return {
          token: parsed.state.token,
          refreshToken: parsed.state.refreshToken,
          user: parsed.state.user,
          isAuthenticated: true,
        }
      }
    }
  } catch {}
  return {}
}

const initial = loadAuth()

export const useAuthStore = create<AuthState>()((set) => ({
  token: initial.token || null,
  refreshToken: initial.refreshToken || null,
  user: initial.user || null,
  isAuthenticated: initial.isAuthenticated || false,

  setAuth: (token, refreshToken, user) => {
    // 同步写入 localStorage
    localStorage.setItem('auth-storage', JSON.stringify({
      state: { token, refreshToken, user, isAuthenticated: true },
      version: 0,
    }))
    set({ token, refreshToken, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('auth-storage')
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false })
  },

  updateUser: (user) => {
    const token = useAuthStore.getState().token
    const refreshToken = useAuthStore.getState().refreshToken
    localStorage.setItem('auth-storage', JSON.stringify({
      state: { token, refreshToken, user, isAuthenticated: true },
      version: 0,
    }))
    set({ user })
  },
}))
