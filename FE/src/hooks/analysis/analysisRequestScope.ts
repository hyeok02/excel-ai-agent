export interface AnalysisRequestScope {
  analysisId: string | null
  signal: AbortSignal
  isActive: () => boolean
}

/** One accepted upload may survive on the server, but only the current view can observe it. */
export const createAnalysisRequestScopes = () => {
  let active: AnalysisRequestScope | undefined
  let controller: AbortController | undefined
  const cancel = () => {
    active = undefined
    controller?.abort()
    controller = undefined
  }
  return {
    cancel,
    differsFrom: (id: string | null) => Boolean(active && active.analysisId !== id),
    begin: (analysisId: string | null): AnalysisRequestScope => {
      cancel()
      controller = new AbortController()
      const scope: AnalysisRequestScope = {
        analysisId,
        signal: controller.signal,
        isActive: () => active === scope && !scope.signal.aborted,
      }
      active = scope
      return scope
    },
  }
}
