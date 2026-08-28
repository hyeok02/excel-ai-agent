import { useEffect, useState } from 'react'

import type { AnalysisStatus } from '@/api/analysis'

const FIRST_PROCESSING_STEP = 2
const LAST_PROCESSING_STEP = 5

export const useAnalysisProgress = () => {
  const [activeStep, setActiveStep] = useState(0)
  const [processingStatus, setProcessingStatus] = useState<AnalysisStatus | null>(null)

  useEffect(() => {
    if (processingStatus !== 'PROCESSING') return undefined

    const intervalId = window.setInterval(() => {
      setActiveStep((current) =>
        Math.min(Math.max(current + 1, FIRST_PROCESSING_STEP), LAST_PROCESSING_STEP),
      )
    }, 1800)

    return () => window.clearInterval(intervalId)
  }, [processingStatus])

  const updateStatus = (nextStatus: AnalysisStatus) => {
    setProcessingStatus(nextStatus)
    if (nextStatus === 'QUEUED') setActiveStep(1)
    if (nextStatus === 'PROCESSING') {
      setActiveStep((current) => Math.max(current, FIRST_PROCESSING_STEP))
    }
    if (nextStatus === 'COMPLETED') setActiveStep(6)
  }

  const reset = (hasSelectedFile: boolean) => {
    setProcessingStatus(null)
    setActiveStep(hasSelectedFile ? 1 : 0)
  }

  return {
    activeStep,
    begin: () => setActiveStep(1),
    processingStatus,
    reset,
    updateStatus,
  }
}
