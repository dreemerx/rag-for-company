import React from 'react'
import { Layout, Avatar, Dropdown, Space, Tag } from 'antd'
import {
  UserOutlined,
  LogoutOutlined,
  MessageOutlined,
  BookOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const { Header, Content } = Layout

const MainLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const isAdmin = user?.roles?.includes('admin')

  const navItems = [
    { key: '/', label: '智能对话', icon: <MessageOutlined /> },
    { key: '/knowledge', label: '知识库', icon: <BookOutlined /> },
  ]
  if (isAdmin) {
    navItems.push({ key: '/admin', label: '管理', icon: <SettingOutlined /> })
  }

  const userMenuItems = [
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ]

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout()
      navigate('/login')
    }
  }

  return (
    <Layout style={{ height: '100vh' }}>
      <Header
        style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
          height: 56,
        }}
      >
        <Space size={24}>
          <span style={{ fontSize: 18, fontWeight: 600, color: '#1677ff' }}>
            🤖 企业智能助手
          </span>
          {navItems.map((item) => (
            <a
              key={item.key}
              onClick={() => navigate(item.key)}
              style={{
                color: location.pathname === item.key ? '#1677ff' : '#666',
                fontWeight: location.pathname === item.key ? 600 : 400,
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              {item.icon} {item.label}
            </a>
          ))}
        </Space>

        <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }} placement="bottomRight">
          <Space style={{ cursor: 'pointer' }}>
            <Avatar size={28} icon={<UserOutlined />} />
            <span style={{ fontSize: 14 }}>{user?.full_name || user?.username}</span>
            {isAdmin && <Tag color="blue" style={{ marginLeft: 0 }}>管理员</Tag>}
          </Space>
        </Dropdown>
      </Header>
      <Content style={{ background: '#f5f5f5', overflow: 'hidden' }}>
        <Outlet />
      </Content>
    </Layout>
  )
}

export default MainLayout
