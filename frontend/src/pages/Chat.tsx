import React, { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, List, Avatar, Typography, Space, message, Spin } from 'antd'
import { SendOutlined, UserOutlined, RobotOutlined, ClearOutlined } from '@ant-design/icons'
import { useChatStore } from '../store/chat'
import ReactMarkdown from 'react-markdown'

const { Text } = Typography

const Chat: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const { messages, sessionId, loading, addMessage, setSessionId, setLoading, clearMessages } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    const messageText = inputValue.trim()
    if (!messageText) return

    // 添加用户消息
    addMessage({ role: 'user', content: messageText })
    setInputValue('')
    setLoading(true)

    try {
      // 使用 SSE 流式输出
      const token = JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token

      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: messageText,
          session_id: sessionId || undefined,
        }),
      })

      if (!response.ok) {
        throw new Error('请求失败')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullReply = ''

      // 添加一个空的助手消息
      addMessage({ role: 'assistant', content: '' })

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'session') {
                setSessionId(data.session_id)
              } else if (data.type === 'chunk') {
                fullReply += data.content
                // 更新最后一条消息
                useChatStore.getState().updateLastMessage(fullReply)
              } else if (data.type === 'done') {
                // 流式输出完成
              } else if (data.type === 'error') {
                message.error(data.message)
              }
            } catch {}
          }
        }
      }
    } catch (error: any) {
      message.error(error.message || '发送失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    clearMessages()
    message.success('对话已清空')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Card
      title={
        <Space>
          <RobotOutlined />
          <span>智能对话</span>
        </Space>
      }
      extra={
        <Button icon={<ClearOutlined />} onClick={handleClear} size="small">
          清空对话
        </Button>
      }
      style={{ height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}
      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: 0 } }}
    >
      {/* 消息列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
        <List
          dataSource={messages}
          renderItem={(msg) => (
            <List.Item style={{ border: 'none', padding: '8px 0' }}>
              <List.Item.Meta
                avatar={
                  <Avatar
                    icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    style={{
                      backgroundColor: msg.role === 'user' ? '#1677ff' : '#52c41a',
                    }}
                  />
                }
                title={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {msg.role === 'user' ? '我' : '智能助手'}
                  </Text>
                }
                description={
                  <div style={{
                    background: msg.role === 'user' ? '#e6f4ff' : '#f6ffed',
                    padding: '12px 16px',
                    borderRadius: 8,
                    maxWidth: '80%',
                  }}>
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
        {loading && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin tip="思考中..." />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div style={{ padding: '16px 24px', borderTop: '1px solid #f0f0f0' }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题... (Enter发送，Shift+Enter换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            style={{ height: 'auto' }}
          >
            发送
          </Button>
        </Space.Compact>
      </div>
    </Card>
  )
}

export default Chat
