interface QuestionHistoryNoticeProps {
  isLoading: boolean
  errorMessage: string | null
  onRetry: () => void
}

const QuestionHistoryNotice = ({
  isLoading,
  errorMessage,
  onRetry,
}: QuestionHistoryNoticeProps) => {
  if (isLoading) {
    return (
      <p className="mb-3 text-sm text-slate-500" role="status">
        이전 대화를 불러오고 있습니다.
      </p>
    )
  }
  if (!errorMessage) return null
  return (
    <div className="mb-3 rounded-2xl bg-amber-50 p-4 text-sm text-amber-800" role="alert">
      <p>이전 대화를 불러오지 못했습니다. 대화가 누락되지 않도록 다시 불러와 주세요.</p>
      <p className="mt-1 text-xs">{errorMessage}</p>
      <button
        className="mt-2 rounded-lg border border-amber-300 px-3 py-2 font-bold"
        onClick={onRetry}
        type="button"
      >
        대화 다시 불러오기
      </button>
    </div>
  )
}

export default QuestionHistoryNotice
