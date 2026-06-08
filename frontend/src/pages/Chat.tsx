import React, { useState, useRef, useEffect } from 'react'
import { Input, Button, List, Avatar, Typography, Spin, Popconfirm, message } from 'antd'
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import { useChatStore } from '../store/chat'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'

const { Text } = Typography

const Chat: React.FC = () => {
  const [inputValue, setInputValue] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sendingSessionIdRef = useRef<number | null>(null)
  // 保存每个对话的流式响应 { sessionId: replyContent }
  const streamingRepliesRef = useRef<Record<number, string>>({})
  // 保存流式响应开始时的消息列表 { sessionId: messages }
  const savedMessagesRef = useRef<Record<number, any[]>>({})

  const {
    sessions,
    currentSessionId,
    messages,
    loading,
    loadingSessions,
    loadSessions,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    addMessage,
    updateLastMessage,
    setLoading,
  } = useChatStore()

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ==================== 发送消息 ====================

  const handleSend = async () => {
    const text = inputValue.trim()
    if (!text || loading) return

    let sessionId = currentSessionId

    // 如果没有当前对话，先创建
    if (!sessionId) {
      try {
        sessionId = await createSession()
      } catch {
        message.error('创建对话失败')
        return
      }
    }

    // 记录本次发送所属的对话 ID
    const sendingSessionId = sessionId
    sendingSessionIdRef.current = sessionId
    streamingRepliesRef.current[sessionId] = ''

    addMessage({ role: 'user', content: text })
    addMessage({ role: 'assistant', content: '' })

    // 保存当前消息列表（包含 user 和 assistant 消息）
    savedMessagesRef.current[sessionId] = [...useChatStore.getState().messages]
    setInputValue('')
    setLoading(true)

    try {
      const token = JSON.parse(localStorage.getItem('auth-storage') || '{}')?.state?.token

      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          message.error('登录已过期，请重新登录')
          return
        }
        throw new Error(`请求失败 (${response.status})`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullReply = ''
      let buffer = ''  // SSE 缓冲区，处理跨 chunk 的不完整行

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // 保留最后一行（可能不完整）
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          const jsonStr = trimmed.slice(6)
          if (!jsonStr) continue

          try {
            const data = JSON.parse(jsonStr)
            if (data.type === 'session' && data.session_id !== currentSessionId) {
              useChatStore.setState({ currentSessionId: data.session_id })
            } else if (data.type === 'chunk') {
              fullReply += data.content
              streamingRepliesRef.current[sendingSessionId] = fullReply
              // 只有当前对话仍是本次发送的对话时才更新 UI
              const currentSid = useChatStore.getState().currentSessionId
              if (currentSid === sendingSessionId) {
                updateLastMessage(fullReply)
              }
            } else if (data.type === 'done' && data.title) {
              // 直接更新本地状态中的标题（不发 API）
              const sid = useChatStore.getState().currentSessionId
              if (sid) {
                useChatStore.setState((state) => ({
                  sessions: state.sessions.map((s) =>
                    s.id === sid ? { ...s, title: data.title } : s
                  ),
                }))
              }
            } else if (data.type === 'error') {
              message.error(data.message || '服务器错误')
            }
          } catch (parseErr) {
            // SSE JSON 解析失败，记录但继续处理
            console.warn('SSE 解析失败:', jsonStr, parseErr)
          }
        }
      }

      // 处理缓冲区中剩余的数据
      if (buffer.trim()) {
        const trimmed = buffer.trim()
        if (trimmed.startsWith('data: ')) {
          try {
            const data = JSON.parse(trimmed.slice(6))
            if (data.type === 'error') {
              message.error(data.message || '服务器错误')
            }
          } catch {
            console.warn('SSE 缓冲区解析失败:', buffer)
          }
        }
      }

      // 刷新对话列表
      loadSessions()
    } catch (e: any) {
      message.error(e.message || '发送失败')
      console.error('对话发送异常:', e)
    } finally {
      setLoading(false)
      sendingSessionIdRef.current = null
      delete streamingRepliesRef.current[sendingSessionId]
      delete savedMessagesRef.current[sendingSessionId]
    }
  }

  // ==================== 对话管理 ====================

  const handleNewChat = async () => {
    try {
      await createSession()
    } catch {
      message.error('创建对话失败')
    }
  }

  const handleDelete = async (id: number, e?: React.MouseEvent) => {
    e?.stopPropagation()
    try {
      await deleteSession(id)
      message.success('已删除')
    } catch {
      message.error('删除失败')
    }
  }

  const handleRename = async (id: number) => {
    if (!editTitle.trim()) return
    try {
      await renameSession(id, editTitle.trim())
      setEditingId(null)
    } catch {
      message.error('重命名失败')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 切换对话
  const handleSwitchSession = async (sessionId: number) => {
    // 如果正在流式响应中，且目标对话就是当前发送的对话
    if (loading && sendingSessionIdRef.current === sessionId) {
      // 使用保存的消息列表，更新流式响应内容
      const savedMessages = savedMessagesRef.current[sessionId]
      const streamingReply = streamingRepliesRef.current[sessionId]
      if (savedMessages) {
        const msgs = [...savedMessages]
        // 更新最后一条消息（assistant）的内容
        if (msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant') {
          msgs[msgs.length - 1] = {
            ...msgs[msgs.length - 1],
            content: streamingReply || '',
          }
        }
        useChatStore.setState({ currentSessionId: sessionId, messages: msgs })
      } else {
        useChatStore.setState({ currentSessionId: sessionId })
      }
      return
    }
    await switchSession(sessionId)
  }

  // ==================== 渲染 ====================

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 56px)' }}>
      {/* 左侧对话列表 */}
      <div
        style={{
          width: 260,
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 新建按钮 */}
        <div style={{ padding: 12 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={handleNewChat}
          >
            新建对话
          </Button>
        </div>

        {/* 对话列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
          <List
            loading={loadingSessions}
            dataSource={sessions}
            renderItem={(session) => (
              <div
                onClick={() => editingId !== session.id && handleSwitchSession(session.id)}
                style={{
                  padding: '10px 12px',
                  marginBottom: 4,
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: currentSessionId === session.id ? '#e6f4ff' : 'transparent',
                  transition: 'background 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
                onMouseEnter={(e) => {
                  if (currentSessionId !== session.id) {
                    (e.currentTarget as HTMLElement).style.background = '#fafafa'
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentSessionId !== session.id) {
                    (e.currentTarget as HTMLElement).style.background = 'transparent'
                  }
                }}
              >
                {editingId === session.id ? (
                  <div style={{ display: 'flex', gap: 4, flex: 1 }} onClick={(e) => e.stopPropagation()}>
                    <Input
                      size="small"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onPressEnter={() => handleRename(session.id)}
                      autoFocus
                    />
                    <Button
                      type="text"
                      size="small"
                      icon={<CheckOutlined />}
                      onClick={() => handleRename(session.id)}
                    />
                    <Button
                      type="text"
                      size="small"
                      icon={<CloseOutlined />}
                      onClick={() => setEditingId(null)}
                    />
                  </div>
                ) : (
                  <>
                    <Text
                      ellipsis
                      style={{
                        flex: 1,
                        color: currentSessionId === session.id ? '#1677ff' : '#333',
                        fontSize: 13,
                      }}
                    >
                      {session.title}
                    </Text>
                    <div style={{ display: 'flex', gap: 2, opacity: 0.5 }} onClick={(e) => e.stopPropagation()}>
                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingId(session.id)
                          setEditTitle(session.title)
                        }}
                      />
                      <Popconfirm
                        title="确定删除这个对话？"
                        onConfirm={() => handleDelete(session.id)}
                        okText="删除"
                        cancelText="取消"
                      >
                        <Button type="text" size="small" icon={<DeleteOutlined />} danger />
                      </Popconfirm>
                    </div>
                  </>
                )}
              </div>
            )}
          />
        </div>
      </div>

      {/* 右侧对话区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'auto', padding: '24px 48px' }}>
          {messages.length === 0 ? (
            <div
              style={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                color: '#bbb',
              }}
            >
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16 }} />
              <Text type="secondary" style={{ fontSize: 16 }}>
                有什么可以帮你的？
              </Text>
            </div>
          ) : (
            <List
              dataSource={messages}
              renderItem={(msg) => (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: 20,
                  }}
                >
                  {msg.role === 'assistant' && (
                    <Avatar
                      icon={<RobotOutlined />}
                      style={{ backgroundColor: '#52c41a', marginRight: 12, flexShrink: 0 }}
                    />
                  )}
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '12px 16px',
                      borderRadius: 12,
                      background: msg.role === 'user' ? '#1677ff' : '#f6f6f6',
                      color: msg.role === 'user' ? '#fff' : '#333',
                      fontSize: 14,
                      lineHeight: 1.8,
                      boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                    }}
                  >
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{msg.content}</ReactMarkdown>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                  </div>
                  {msg.role === 'user' && (
                    <Avatar
                      icon={<UserOutlined />}
                      style={{ backgroundColor: '#1677ff', marginLeft: 12, flexShrink: 0 }}
                    />
                  )}
                </div>
              )}
            />
          )}
          {loading && messages.length > 0 && messages[messages.length - 1]?.content === '' && (
            <div style={{ display: 'flex', alignItems: 'center', padding: '0 0 20px 52px' }}>
              <Spin size="small" />
              <Text type="secondary" style={{ marginLeft: 8, fontSize: 13 }}>思考中...</Text>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div
          style={{
            padding: '16px 48px 24px',
            borderTop: '1px solid #f0f0f0',
            background: '#fff',
          }}
        >
          <div style={{ display: 'flex', gap: 12, maxWidth: 800, margin: '0 auto' }}>
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="输入你的问题... (Enter 发送，Shift+Enter 换行)"
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={loading}
              style={{ borderRadius: 8 }}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              loading={loading}
              style={{ height: 'auto', borderRadius: 8, minWidth: 48 }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat
