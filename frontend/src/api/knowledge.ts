/**
 * 知识库 API 模块
 * - 封装知识库统计、文档上传、清空等 API
 */
import apiClient from './client'

/** 知识库统计接口 */
export interface KnowledgeStats {
  document_count: number    // 文档块数量
}

/** 上传响应接口 */
export interface UploadResponse {
  message: string           // 响应消息
  total: number             // 上传总数
}

/** 知识库 API */
export const knowledgeApi = {
  /** 获取知识库统计信息 */
  getStats: () =>
    apiClient.get<KnowledgeStats>('/knowledge/stats'),

  /** 上传文档到知识库 */
  uploadDocuments: (files: File[]) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return apiClient.post<UploadResponse>('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 清空知识库 */
  clearKnowledge: () =>
    apiClient.delete('/knowledge/clear'),
}
