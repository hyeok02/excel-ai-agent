import type {
  AnalysisDepth,
  AnalysisDetails,
  AnalysisMode,
  AnalysisResultDetails,
  AnalysisStatus,
  AnalysisSubmission,
  CompletedAnalysis,
} from './jobTypes.ts'

interface JobTransport {
  submit: (
    file: File,
    mode: AnalysisMode,
    depth: AnalysisDepth,
    includeHiddenSheets: boolean,
    signal?: AbortSignal,
  ) => Promise<AnalysisSubmission>
  details: (id: string, signal?: AbortSignal) => Promise<AnalysisDetails>
  result: (id: string, signal?: AbortSignal) => Promise<AnalysisResultDetails>
  timeoutMs: number
  pollIntervalMs: number
}

/** Cancelling observation never deletes or cancels the accepted server job. */
export const waitForAnalysisPoll = (delay: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    signal?.throwIfAborted()
    const finish = () => {
      signal?.removeEventListener('abort', abort)
      resolve()
    }
    const timer = setTimeout(finish, delay)
    const abort = () => {
      clearTimeout(timer)
      signal?.removeEventListener('abort', abort)
      reject(signal?.reason)
    }
    signal?.addEventListener('abort', abort, { once: true })
  })

export const createAnalysisJobRunner = (transport: JobTransport) => {
  const waitForAnalysis = async (
    id: string,
    onStatus?: (status: AnalysisStatus) => void,
    signal?: AbortSignal,
  ) => {
    const startedAt = Date.now()
    while (Date.now() - startedAt < transport.timeoutMs) {
      signal?.throwIfAborted()
      const details = await transport.details(id, signal)
      signal?.throwIfAborted()
      onStatus?.(details.status)
      if (details.status === 'COMPLETED') return
      if (details.status === 'FAILED') {
        throw new Error(details.failureMessage ?? 'Excel 분석 처리에 실패했습니다.')
      }
      await waitForAnalysisPoll(transport.pollIntervalMs, signal)
    }
    throw new Error(
      '분석 대기 시간이 초과되었습니다. 분석 이력에서 처리 상태를 확인해주세요.',
    )
  }

  return {
    analyze: async (
      file: File,
      mode: AnalysisMode,
      depth: AnalysisDepth,
      includeHiddenSheets: boolean,
      onStatus?: (status: AnalysisStatus) => void,
      onSubmitted?: (submission: AnalysisSubmission) => void,
      signal?: AbortSignal,
    ): Promise<CompletedAnalysis> => {
      signal?.throwIfAborted()
      const submission = await transport.submit(
        file,
        mode,
        depth,
        includeHiddenSheets,
        signal,
      )
      signal?.throwIfAborted()
      onSubmitted?.(submission)
      signal?.throwIfAborted()
      onStatus?.(submission.status)
      await waitForAnalysis(submission.analysisId, onStatus, signal)
      signal?.throwIfAborted()
      const result = await transport.result(submission.analysisId, signal)
      signal?.throwIfAborted()
      return { submission, result }
    },
    resume: async (
      id: string,
      onStatus?: (status: AnalysisStatus) => void,
      signal?: AbortSignal,
    ): Promise<CompletedAnalysis> => {
      signal?.throwIfAborted()
      const submission = await transport.details(id, signal)
      signal?.throwIfAborted()
      onStatus?.(submission.status)
      if (submission.status === 'FAILED') {
        throw new Error(
          submission.failureMessage ?? '이 분석은 처리에 실패하여 결과를 열 수 없습니다.',
        )
      }
      if (submission.status !== 'COMPLETED') {
        await waitForAnalysis(id, onStatus, signal)
      }
      signal?.throwIfAborted()
      const result = await transport.result(id, signal)
      signal?.throwIfAborted()
      return { submission, result }
    },
  }
}
