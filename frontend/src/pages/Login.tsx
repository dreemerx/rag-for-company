import React, { useState } from 'react'
import { Card, Input, Button, message, Tabs, Space } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, TeamOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import { authApi } from '../api/auth'

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')
  const setAuth = useAuthStore((state) => state.setAuth)

  // 登录表单状态
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  // 注册表单状态
  const [registerForm, setRegisterForm] = useState({ username: '', email: '', password: '', full_name: '', department: '' })

  const handleLogin = async () => {
    if (!loginForm.username || !loginForm.password) {
      message.warning('请输入用户名和密码')
      return
    }

    setLoading(true)
    try {
      const { data } = await authApi.login(loginForm)
      console.log('Login success, token:', data.access_token)

      let userInfo: any = {
        id: 0,
        username: loginForm.username,
        email: '',
        full_name: null,
        department: null,
        is_active: true,
        roles: ['user'],
        created_at: new Date().toISOString(),
      }

      try {
        const { data: user } = await authApi.getMe()
        userInfo = user
      } catch {}

      // setAuth 内部会同步写入 localStorage
      setAuth(data.access_token, data.refresh_token, userInfo)
      message.success('登录成功')

      // 直接跳转
      window.location.href = '/'
    } catch (error: any) {
      console.error('Login error:', error)
      message.error(error.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    if (!registerForm.username || !registerForm.email || !registerForm.password) {
      message.warning('请填写必填项')
      return
    }

    setLoading(true)
    try {
      await authApi.register(registerForm)
      message.success('注册成功，请登录')
      setActiveTab('login')
      setLoginForm({ username: registerForm.username, password: '' })
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  const loginContent = (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Input
        size="large"
        prefix={<UserOutlined />}
        placeholder="用户名"
        value={loginForm.username}
        onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
        onPressEnter={handleLogin}
      />
      <Input.Password
        size="large"
        prefix={<LockOutlined />}
        placeholder="密码"
        value={loginForm.password}
        onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
        onPressEnter={handleLogin}
      />
      <Button type="primary" size="large" block loading={loading} onClick={handleLogin}>
        登录
      </Button>
    </Space>
  )

  const registerContent = (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Input
        size="large"
        prefix={<UserOutlined />}
        placeholder="用户名 *"
        value={registerForm.username}
        onChange={(e) => setRegisterForm({ ...registerForm, username: e.target.value })}
      />
      <Input
        size="large"
        prefix={<MailOutlined />}
        placeholder="邮箱 *"
        value={registerForm.email}
        onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
      />
      <Input.Password
        size="large"
        prefix={<LockOutlined />}
        placeholder="密码 *"
        value={registerForm.password}
        onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
      />
      <Input
        size="large"
        prefix={<UserOutlined />}
        placeholder="姓名（选填）"
        value={registerForm.full_name}
        onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })}
      />
      <Input
        size="large"
        prefix={<TeamOutlined />}
        placeholder="部门（选填）"
        value={registerForm.department}
        onChange={(e) => setRegisterForm({ ...registerForm, department: e.target.value })}
      />
      <Button type="primary" size="large" block loading={loading} onClick={handleRegister}>
        注册
      </Button>
    </Space>
  )

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, borderRadius: 8 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>企业 RAG 智能助手</h1>
          <p style={{ color: '#666' }}>面向企业内部员工的智能问答系统</p>
        </div>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          centered
          items={[
            { key: 'login', label: '登录', children: loginContent },
            { key: 'register', label: '注册', children: registerContent },
          ]}
        />
      </Card>
    </div>
  )
}

export default Login
