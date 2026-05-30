import React, { useState, useEffect } from 'react'
import { Card, Upload, Button, Statistic, Row, Col, message, Popconfirm, Space, Typography } from 'antd'
import { UploadOutlined, DeleteOutlined, FileTextOutlined, InboxOutlined } from '@ant-design/icons'
import { knowledgeApi, KnowledgeStats } from '../api/knowledge'
import { useAuthStore } from '../store/auth'
import type { UploadFile } from 'antd/es/upload/interface'

const { Dragger } = Upload
const { Title } = Typography

const KnowledgeBase: React.FC = () => {
  const [stats, setStats] = useState<KnowledgeStats>({ document_count: 0 })
  const [loading, setLoading] = useState(false)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const user = useAuthStore((state) => state.user)
  const isAdmin = user?.roles?.includes('admin')

  const fetchStats = async () => {
    try {
      const { data } = await knowledgeApi.getStats()
      setStats(data)
    } catch (error) {
      message.error('获取统计信息失败')
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件')
      return
    }

    setLoading(true)
    try {
      const files = fileList.map((f) => f.originFileObj as File)
      const { data } = await knowledgeApi.uploadDocuments(files)
      message.success(data.message)
      setFileList([])
      fetchStats()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    try {
      await knowledgeApi.clearKnowledge()
      message.success('知识库已清空')
      fetchStats()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '清空失败')
    }
  }

  const uploadProps = {
    multiple: true,
    accept: '.pdf,.docx,.doc,.md,.txt',
    fileList,
    beforeUpload: (file: File) => {
      setFileList((prev) => [...prev, { uid: file.name, name: file.name, originFileObj: file } as UploadFile])
      return false
    },
    onRemove: (file: UploadFile) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid))
    },
  }

  return (
    <div>
      <Title level={3}>📚 知识库管理</Title>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="文档数量"
              value={stats.document_count}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 上传区域 */}
      <Card title="上传文档" style={{ marginBottom: 24 }}>
        <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PDF、Word、Markdown、TXT 格式
          </p>
        </Dragger>

        <Space>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={handleUpload}
            loading={loading}
            disabled={fileList.length === 0}
          >
            开始上传
          </Button>
          {fileList.length > 0 && (
            <Button onClick={() => setFileList([])}>清空选择</Button>
          )}
        </Space>
      </Card>

      {/* 管理员操作 */}
      {isAdmin && (
        <Card title="管理员操作">
          <Popconfirm
            title="确定要清空知识库吗？此操作不可恢复。"
            onConfirm={handleClear}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>
              清空知识库
            </Button>
          </Popconfirm>
        </Card>
      )}
    </div>
  )
}

export default KnowledgeBase
