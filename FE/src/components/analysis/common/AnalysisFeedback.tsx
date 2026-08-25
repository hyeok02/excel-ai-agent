import { CheckCircle2, X } from 'lucide-react'

import type { AnalysisFeedback as Feedback } from '@/hooks/analysis/useWorkbookAnalysis'

interface AnalysisFeedbackProps {
  feedback: Feedback | null
}

const AnalysisFeedback = ({ feedback }: AnalysisFeedbackProps) => {
  if (!feedback) {
    return null
  }

  const isSuccess = feedback === 'success'

  return (
    <div
      aria-live="assertive"
      className="analysis-feedback-overlay"
      role={isSuccess ? 'status' : 'alert'}
    >
      <div className="analysis-feedback-card" data-result={feedback}>
        <span className="analysis-feedback-icon">
          {isSuccess ? (
            <CheckCircle2 aria-hidden="true" size={54} strokeWidth={1.8} />
          ) : (
            <X aria-hidden="true" size={54} strokeWidth={2} />
          )}
        </span>
        <strong>{isSuccess ? '분석 완료' : '분석 실패'}</strong>
        <span>
          {isSuccess ? '결과를 성공적으로 불러왔어요' : '오류 내용을 확인해주세요'}
        </span>
      </div>
    </div>
  )
}

export default AnalysisFeedback
