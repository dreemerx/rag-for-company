import React, { useState, useEffect } from 'react'
import { Card, Upload, Button, Statistic, Row, Col, message, Popconfirm, Typography, Space } from 'antd'
import { UploadOutlined, DeleteOutlined, FileTextOutlined, InboxOutlined } from '@ant-design/icons'
import { knowledgeApi, KnowledgeStats } from '../api/knowledge'
import { useAuthStore } from '../store/auth'
import type { UploadFile } from 'antd/es/upload/interface'

const { Dragger } = Upload
const { Title, Text } = Typography

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
    } catch {}
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleUpload = async () => {
    if (fileList.length === 0) return
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
    <div style={{ height: '100%', padding: '24px', overflow: 'auto' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <Title level={4} style={{ marginBottom: 24 }}>📚 知识库管理</Title>

        {/* 统计卡片 */}
        <Card style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic title="文档数量" value={stats.document_count} prefix={<FileTextOutlined />} />
            </Col>
          </Row>
        </Card>

        {isAdmin ? (
          <>
            {/* 上传文档卡片 */}
            <Card title="上传文档" style={{ marginBottom: 24 }}>
              <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">支持 PDF、Word、Markdown、TXT 格式</p>
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
                  <Text type="secondary">已选择 {fileList.length} 个文件</Text>
                )}
              </Space>
            </Card>

            {/* 管理员操作卡片 */}
            <Card title="管理员操作">
              <Space direction="vertical" size="middle">
                <Text type="secondary">清空知识库将删除所有已上传的文档，此操作不可恢复。</Text>
                <Popconfirm
                  title="确定要清空知识库吗？"
                  description="此操作将删除所有文档，且不可恢复。"
                  onConfirm={handleClear}
                  okText="确定清空"
                  cancelText="取消"
                  okButtonProps={{ danger: true }}
                >
                  <Button danger icon={<DeleteOutlined />} size="large">
                    清空知识库
                  </Button>
                </Popconfirm>
              </Space>
            </Card>
          </>
        ) : (
          <Card>
            <Space direction="vertical" align="center" style={{ width: '100%', padding: '24px 0' }}>
              <FileTextOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
              <Text type="secondary" style={{ fontSize: 16 }}>
                知识库文档由管理员维护
              </Text>
              <Text type="secondary">如有需要请联系管理员上传文档。</Text>
            </Space>
          </Card>
        )}
      </div>
    </div>
  )
}

export default KnowledgeBase
