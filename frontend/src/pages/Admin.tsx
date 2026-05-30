import React, { useState } from 'react'
import { Card, Tabs, Table, Button, message, Statistic, Row, Col, Tag, Typography } from 'antd'
import { PlayCircleOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { useAuthStore } from '../store/auth'
import apiClient from '../api/client'

const { Title } = Typography

interface EvalResult {
  total: number
  passed: number
  failed: number
  accuracy: number
  category_accuracy: Record<string, number>
}

const Admin: React.FC = () => {
  const user = useAuthStore((state) => state.user)
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null)
  const [evalLoading, setEvalLoading] = useState(false)

  if (!user?.roles?.includes('admin')) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
        <Card>
          <Title level={4}>无权限访问</Title>
          <p>此页面仅管理员可访问。</p>
        </Card>
      </div>
    )
  }

  const handleRunEval = async () => {
    setEvalLoading(true)
    try {
      const { data } = await apiClient.post('/evaluation/run')
      setEvalResult(data)
      message.success('评测完成')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '评测失败')
    } finally {
      setEvalLoading(false)
    }
  }

  const evalColumns = [
    { title: '类别', dataIndex: 'category', key: 'category' },
    {
      title: '准确率',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (val: number) => `${(val * 100).toFixed(1)}%`,
    },
    {
      title: '状态',
      key: 'status',
      render: (_: any, record: any) => (
        <Tag color={record.accuracy >= 0.85 ? 'green' : 'red'}>
          {record.accuracy >= 0.85 ? '达标' : '未达标'}
        </Tag>
      ),
    },
  ]

  const evalData = evalResult
    ? Object.entries(evalResult.category_accuracy).map(([category, accuracy]) => ({ category, accuracy }))
    : []

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '32px 24px' }}>
      <Title level={4} style={{ marginBottom: 24 }}>⚙️ 系统管理</Title>

      <Tabs
        items={[
          {
            key: 'eval',
            label: '系统评测',
            children: (
              <>
                <Card style={{ marginBottom: 24 }}>
                  <Row gutter={16}>
                    <Col span={6}><Statistic title="总用例数" value={evalResult?.total || 0} /></Col>
                    <Col span={6}>
                      <Statistic title="通过" value={evalResult?.passed || 0} valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} />
                    </Col>
                    <Col span={6}>
                      <Statistic title="失败" value={evalResult?.failed || 0} valueStyle={{ color: '#cf1322' }} prefix={<WarningOutlined />} />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="准确率"
                        value={evalResult ? (evalResult.accuracy * 100).toFixed(1) : 0}
                        suffix="%"
                        valueStyle={{ color: (evalResult?.accuracy || 0) >= 0.85 ? '#3f8600' : '#cf1322' }}
                      />
                    </Col>
                  </Row>
                </Card>
                <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleRunEval} loading={evalLoading} style={{ marginBottom: 16 }}>
                  运行评测
                </Button>
                <Table columns={evalColumns} dataSource={evalData} rowKey="category" pagination={false} />
              </>
            ),
          },
          {
            key: 'users',
            label: '用户管理',
            children: <Card><p style={{ color: '#999' }}>用户管理功能开发中...</p></Card>,
          },
        ]}
      />
    </div>
  )
}

export default Admin
