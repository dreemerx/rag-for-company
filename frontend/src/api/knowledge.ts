import apiClient from './client'

export interface KnowledgeStats {
  document_count: number
}

export interface UploadResponse {
  message: string
  total: number
}

export const knowledgeApi = {
  getStats: () =>
    apiClient.get<KnowledgeStats>('/knowledge/stats'),

  uploadDocuments: (files: File[]) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return apiClient.post<UploadResponse>('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  clearKnowledge: () =>
    apiClient.delete('/knowledge/clear'),
}
