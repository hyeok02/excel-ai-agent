import { useInfiniteQuery } from '@tanstack/react-query'
import { LoaderCircle, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { type AnalysisHistoryPage, getAnalysisHistory } from '@/api/analysis'
import AnalysisHistoryItem from '@/components/analysis/upload/AnalysisHistoryItem'
import { HISTORY_PAGE_SIZE } from '@/components/analysis/upload/analysisHistoryPresentation'

interface AnalysisHistoryDialogProps {
  activeAnalysisId: string | null
  onClose: () => void
  onOpen: (analysisId: string) => void
}

const AnalysisHistoryDialog = ({
  activeAnalysisId,
  onClose,
  onOpen,
}: AnalysisHistoryDialogProps) => {
  const [keyword, setKeyword] = useState('')
  const [filename, setFilename] = useState('')

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setFilename(keyword.trim()), 300)
    return () => window.clearTimeout(timeoutId)
  }, [keyword])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage } =
    useInfiniteQuery({
      getNextPageParam: (last: AnalysisHistoryPage) =>
        last.hasNext ? last.page + 1 : undefined,
      initialPageParam: 0,
      queryFn: ({ pageParam }) =>
        getAnalysisHistory({
          filename: filename || undefined,
          page: pageParam,
          size: HISTORY_PAGE_SIZE,
        }),
      queryKey: ['analysis-history', filename],
    })

  const items = data?.pages.flatMap((page) => page.content) ?? []
  const total = data?.pages[0]?.totalElements ?? 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        aria-label="닫기"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        onClick={onClose}
        type="button"
      />
      <div
        aria-label="분석한 파일 불러오기"
        aria-modal="true"
        className="panel relative flex max-h-[80vh] w-full max-w-2xl flex-col p-6"
        role="dialog"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-extrabold text-slate-950">
              분석한 파일 불러오기
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              예전에 분석한 파일을 선택하면 결과와 근거를 다시 볼 수 있어요.
            </p>
          </div>
          <button
            aria-label="닫기"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <label className="mt-4 flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 focus-within:border-brand-300">
          <Search aria-hidden="true" className="shrink-0 text-slate-400" size={16} />
          <input
            autoFocus
            className="w-full bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="파일명으로 검색"
            value={keyword}
          />
          {isFetching && !isFetchingNextPage && (
            <LoaderCircle
              aria-hidden="true"
              className="animate-spin text-slate-400"
              size={14}
            />
          )}
        </label>

        <p className="mt-3 text-[11px] text-slate-400">
          {filename ? `'${filename}' 검색 결과 ${total}건` : `전체 ${total}건`}
        </p>

        <ul className="mt-2 min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1">
          {items.map((item) => (
            <li key={item.analysisId}>
              <AnalysisHistoryItem
                isActive={item.analysisId === activeAnalysisId}
                item={item}
                onOpen={onOpen}
              />
            </li>
          ))}
          {items.length === 0 && !isFetching && (
            <li className="py-8 text-center text-xs text-slate-400">
              조건에 맞는 분석 기록이 없습니다.
            </li>
          )}
        </ul>

        {hasNextPage && (
          <button
            className="mt-3 shrink-0 rounded-xl border border-slate-200 py-2 text-xs font-extrabold text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
            disabled={isFetchingNextPage}
            onClick={() => void fetchNextPage()}
            type="button"
          >
            {isFetchingNextPage ? '불러오는 중' : '더 보기'}
          </button>
        )}
      </div>
    </div>
  )
}

export default AnalysisHistoryDialog
