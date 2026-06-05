/**
 * 认证状态管理模块
 * - 使用 Zustand 管理用户认证状态
 * - 支持 localStorage 持久化
 * - 提供登录、登出、更新用户信息等操作
 */
import { create } from 'zustand'

/** 用户信息接口 */
interface User {
  id: number                    // 用户 ID
  username: string              // 用户名
  email: string                 // 邮箱
  full_name: string | null      // 姓名
  department: string | null     // 部门
  roles: string[]               // 角色列表
}

/** 认证状态接口 */
interface AuthState {
  token: string | null                      // 访问令牌
  refreshToken: string | null               // 刷新令牌
  user: User | null                         // 用户信息
  isAuthenticated: boolean                  // 是否已认证
  setAuth: (token: string, refreshToken: string, user: User) => void  // 设置认证信息
  logout: () => void                        // 登出
  updateUser: (user: User) => void          // 更新用户信息
}

/**
 * 从 localStorage 读取初始认证状态
 * 应用刷新时恢复登录状态
 */
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

// 加载初始状态
const initial = loadAuth()

/** 认证状态 Store */
export const useAuthStore = create<AuthState>()((set) => ({
  token: initial.token || null,
  refreshToken: initial.refreshToken || null,
  user: initial.user || null,
  isAuthenticated: initial.isAuthenticated || false,

  /**
   * 设置认证信息（登录成功后调用）
   * 同步写入 localStorage 和内存状态
   */
  setAuth: (token, refreshToken, user) => {
    localStorage.setItem('auth-storage', JSON.stringify({
      state: { token, refreshToken, user, isAuthenticated: true },
      version: 0,
    }))
    set({ token, refreshToken, user, isAuthenticated: true })
  },

  /** 登出（清除所有认证信息） */
  logout: () => {
    localStorage.removeItem('auth-storage')
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false })
  },

  /** 更新用户信息（如修改角色后） */
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
