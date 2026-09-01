import type { AnalysisViewStatus } from '@/hooks/analysis/useWorkbookAnalysis'

interface AnalysisHeaderProps {
  status: AnalysisViewStatus
  statusText: string
}

const AnalysisHeader = ({ status, statusText }: AnalysisHeaderProps) => {
  return (
    <section className="panel page-heading p-6 md:p-8">
      <div>
        <p className="eyebrow">엑셀 의사결정 지원</p>
        <h1 className="page-title">Excel 분석</h1>
        <p className="page-description">
          엑셀 파일을 업로드하면 시트별 리전과 수식을 탐지하고, 셀 참조 관계를 구조화하여
          화면에 표시합니다.
        </p>
      </div>
      <span className="status-pill" data-status={status}>
        <span />
        {statusText}
      </span>
    </section>
  )
}

export default AnalysisHeader
