import { stringify as stringifyYaml } from 'yaml'

import type { AnalysisResultDetails } from '@/api/analysis'

export type AnalysisExportFormat = 'json' | 'yaml'

interface AnalysisExportDocument {
  schemaVersion: '1.0'
  exportedAt: string
  analysis: AnalysisResultDetails
}

const sanitizeFilename = (filename: string) => {
  const basename = filename.replace(/\.[^/.]+$/, '')
  const sanitized = basename
    .normalize('NFKC')
    .replace(/[^\p{L}\p{N}._-]+/gu, '-')
    .replace(/^-+|-+$/g, '')

  return sanitized || 'workbook'
}

const createExportDocument = (result: AnalysisResultDetails): AnalysisExportDocument => ({
  schemaVersion: '1.0',
  exportedAt: new Date().toISOString(),
  analysis: result,
})

const serializeExportDocument = (
  document: AnalysisExportDocument,
  format: AnalysisExportFormat,
) => {
  if (format === 'json') {
    return JSON.stringify(document, null, 2)
  }

  return stringifyYaml(document, {
    indent: 2,
    lineWidth: 0,
  })
}

export const downloadAnalysisResult = (
  result: AnalysisResultDetails,
  format: AnalysisExportFormat,
) => {
  const document = createExportDocument(result)
  const content = serializeExportDocument(document, format)
  const mimeType = format === 'json' ? 'application/json' : 'application/yaml'
  const filename = `${sanitizeFilename(result.workbook.filename)}-analysis-${result.analysisId.slice(0, 8)}.${format}`
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` })
  const downloadUrl = URL.createObjectURL(blob)
  const anchor = window.document.createElement('a')

  anchor.href = downloadUrl
  anchor.download = filename
  window.document.body.append(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0)
}
