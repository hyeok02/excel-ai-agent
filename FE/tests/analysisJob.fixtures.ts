import type {
  AnalysisDetails,
  AnalysisResultDetails,
  AnalysisStatus,
} from '../src/api/analysis/jobTypes.ts'

export const deferredJob = <T>() => {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

export const jobDetails = (
  analysisId = 'job-a',
  status: AnalysisStatus = 'COMPLETED',
): AnalysisDetails => ({
  analysisId,
  status,
  mode: 'BFS',
  originalFilename: `${analysisId}.xlsx`,
  sizeBytes: 10,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
  fileExtension: 'xlsx',
  includeHiddenSheets: false,
  sourceAvailable: true,
})

export const jobResult = (analysisId = 'job-a'): AnalysisResultDetails =>
  ({ analysisId, insightReport: null, workbook: {} }) as AnalysisResultDetails

export const jobTransport = () => ({
  submit: async () => jobDetails('job-a', 'QUEUED'),
  details: async (id: string) => jobDetails(id),
  result: async (id: string) => jobResult(id),
  timeoutMs: 1_000,
  pollIntervalMs: 1,
})

export const noFile = new File(['fixture'], 'workbook.xlsx')
