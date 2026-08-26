import { ChevronRight } from 'lucide-react'

import type { HeaderPathResult } from '@/api/analysis'

interface HeaderPathListProps {
  paths: HeaderPathResult[]
}

const HeaderPathList = ({ paths }: HeaderPathListProps) => {
  if (paths.length === 0) return null
  const maxDepth = Math.max(...paths.map((path) => path.labels.length))

  return (
    <div className="mb-3 rounded-xl bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11px] font-extrabold text-slate-500">
          {maxDepth > 1 ? '다중 행 헤더 경로' : '헤더 구조'}
        </p>
        {maxDepth > 1 && (
          <span className="text-[10px] font-bold text-brand-600">
            최대 {maxDepth}단계
          </span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {paths.slice(0, 12).map((path) => (
          <span
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] text-slate-600"
            key={`${path.column}-${path.labels.join('-')}`}
          >
            <b className="mr-1 text-slate-400">{path.column}</b>
            {path.labels.map((label, index) => (
              <span className="inline-flex items-center gap-1" key={`${label}-${index}`}>
                {index > 0 && <ChevronRight aria-hidden="true" size={11} />}
                {label}
              </span>
            ))}
          </span>
        ))}
      </div>
      {paths.length > 12 && (
        <p className="mt-2 text-[10px] text-slate-400">
          나머지 {paths.length - 12}개 열은 내보내기 결과에 포함됩니다.
        </p>
      )}
    </div>
  )
}

export default HeaderPathList
