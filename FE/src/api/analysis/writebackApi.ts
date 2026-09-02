import type { WorkbookWriteback } from '@/api/analysis/writebackTypes'
import apiClient from '@/utils/apiClient'

const base = (analysisId: string) => `/api/v1/analyses/${analysisId}/writebacks`

export const getWorkbookWritebacks = async (analysisId: string) => {
  const { data } = await apiClient.get<WorkbookWriteback[]>(base(analysisId))
  return data
}

export const proposeWorkbookWriteback = async (
  analysisId: string,
  instruction: string,
) => {
  const { data } = await apiClient.post<WorkbookWriteback>(base(analysisId), {
    instruction,
  })
  return data
}

export const approveWorkbookWriteback = async (
  analysisId: string,
  writebackId: string,
) => {
  const { data } = await apiClient.post<WorkbookWriteback>(
    `${base(analysisId)}/${writebackId}/approve`,
    { confirmed: true },
  )
  return data
}

export const rejectWorkbookWriteback = async (
  analysisId: string,
  writebackId: string,
) => {
  const { data } = await apiClient.post<WorkbookWriteback>(
    `${base(analysisId)}/${writebackId}/reject`,
  )
  return data
}

export const downloadWorkbookWriteback = async (
  analysisId: string,
  writebackId: string,
) => {
  const response = await apiClient.get(`${base(analysisId)}/${writebackId}/download`, {
    responseType: 'blob',
  })
  const disposition = String(response.headers['content-disposition'] ?? '')
  const match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const filename = match ? decodeURIComponent(match[1]) : 'modified.xlsx'
  return { blob: response.data as Blob, filename }
}
