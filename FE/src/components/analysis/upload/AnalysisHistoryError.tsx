import { RefreshCw, TriangleAlert } from 'lucide-react'

import { getErrorMessage } from '@/utils/apiClient'

interface AnalysisHistoryErrorProps {
  error: unknown
  onRetry: () => void
}

const AnalysisHistoryError = ({ error, onRetry }: AnalysisHistoryErrorProps) => (
  <li className="rounded-2xl border border-red-100 bg-red-50 p-5 text-center">
    <TriangleAlert className="mx-auto text-red-500" size={22} />
    <p className="mt-2 text-sm font-extrabold text-red-700">
      분석 기록을 불러오지 못했습니다.
    </p>
    <p className="mt-1 text-xs text-red-600">{getErrorMessage(error)}</p>
    <button
      className="mx-auto mt-3 inline-flex items-center gap-1.5 rounded-xl border border-red-200 bg-white px-3 py-2 text-xs font-extrabold text-red-700"
      onClick={onRetry}
      type="button"
    >
      <RefreshCw size={14} /> 다시 시도
    </button>
  </li>
)

export default AnalysisHistoryError
