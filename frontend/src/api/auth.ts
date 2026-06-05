/**
 * 认证 API 模块
 * - 封装登录、注册、刷新令牌等认证相关 API
 */
import apiClient from './client'

/** 登录请求接口 */
export interface LoginRequest {
  username: string      // 用户名
  password: string      // 密码
}

/** 注册请求接口 */
export interface RegisterRequest {
  username: string                // 用户名
  email: string                   // 邮箱
  password: string                // 密码
  full_name?: string              // 姓名（可选）
  department?: string             // 部门（可选）
}

/** Token 响应接口 */
export interface TokenResponse {
  access_token: string            // 访问令牌
  refresh_token: string           // 刷新令牌
  token_type: string              // 令牌类型
}

/** 用户信息响应接口 */
export interface UserResponse {
  id: number                      // 用户 ID
  username: string                // 用户名
  email: string                   // 邮箱
  full_name: string | null        // 姓名
  department: string | null       // 部门
  is_active: boolean              // 是否启用
  roles: string[]                 // 角色列表
  created_at: string              // 创建时间
}

/** 认证 API */
export const authApi = {
  /** 用户登录 */
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data),

  /** 用户注册 */
  register: (data: RegisterRequest) =>
    apiClient.post<UserResponse>('/auth/register', data),

  /** 刷新令牌 */
  refreshToken: (refreshToken: string) =>
    apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

  /** 获取当前用户信息 */
  getMe: () =>
    apiClient.get<UserResponse>('/auth/me'),
}
