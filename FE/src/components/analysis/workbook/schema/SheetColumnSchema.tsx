import { ChevronDown, ChevronUp, Columns3 } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { ColumnSchemaResult } from '@/api/analysis'
import ColumnSchemaCard from '@/components/analysis/workbook/schema/ColumnSchemaCard'
import ColumnSchemaSummary from '@/components/analysis/workbook/schema/ColumnSchemaSummary'
import {
  type ColumnSchemaView,
  columnsForView,
  hasDetectedUnit,
  isClassifiedColumn,
  needsColumnReview,
} from '@/components/analysis/workbook/schema/columnSchemaUtils'

interface SheetColumnSchemaProps {
  columns: ColumnSchemaResult[]
  sheetName: string
}

const SheetColumnSchema = ({ columns, sheetName }: SheetColumnSchemaProps) => {
  const [view, setView] = useState<ColumnSchemaView>('important')
  const [expanded, setExpanded] = useState(false)
  const classifiedCount = columns.filter(isClassifiedColumn).length
  const reviewCount = columns.filter(needsColumnReview).length
  const unitCount = columns.filter(hasDetectedUnit).length
  const importantCount = columnsForView(columns, 'important').length
  const visibleColumns = useMemo(() => columnsForView(columns, view), [columns, view])
  const displayedColumns = expanded ? visibleColumns : visibleColumns.slice(0, 3)

  const changeView = (nextView: ColumnSchemaView) => {
    setView(nextView)
    setExpanded(false)
  }

  if (columns.length === 0) return null

  return (
    <section className="border-t border-slate-100 px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="grid size-8 place-items-center rounded-xl bg-indigo-50 text-indigo-600">
            <Columns3 aria-hidden="true" size={16} />
          </span>
          <div>
            <h4 className="text-xs font-extrabold text-slate-800">
              열 의미와 단위
            </h4>
            <p className="mt-1 text-[11px] text-slate-400">
              Excel의 열 이름을 업무 의미로 정리하고 값의 유형과 단위를 확인했어요.
            </p>
          </div>
        </div>
      </div>

      <ColumnSchemaSummary
        classifiedCount={classifiedCount}
        reviewCount={reviewCount}
        totalCount={columns.length}
        unitCount={unitCount}
      />

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
        <p className="text-[10px] font-bold text-slate-500">
          {view === 'important' ? '주요 의미별 대표 열' : view === 'review' ? '검토가 필요한 열' : '전체 열'}
        </p>
        <div className="flex rounded-lg bg-slate-100 p-0.5 text-[10px] font-bold">
          <ViewButton active={view === 'important'} onClick={() => changeView('important')}>
            주요 {importantCount}
          </ViewButton>
          <ViewButton active={view === 'review'} onClick={() => changeView('review')}>
            검토 필요 {reviewCount}
          </ViewButton>
          <ViewButton active={view === 'all'} onClick={() => changeView('all')}>
            전체 {columns.length}
          </ViewButton>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        {displayedColumns.map((column) => (
          <ColumnSchemaCard
            column={column}
            key={`${column.sourceRange}-${column.column}`}
            sheetName={sheetName}
          />
        ))}
      </div>
      {visibleColumns.length === 0 && (
        <p className="mt-3 rounded-xl bg-emerald-50 px-4 py-3 text-center text-[11px] font-bold text-emerald-700">
          확인이 필요한 미분류 열이 없습니다.
        </p>
      )}
      {visibleColumns.length > 3 && (
        <button
          className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-[11px] font-extrabold text-slate-600 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? (
            <>
              접어보기 <ChevronUp aria-hidden="true" size={14} />
            </>
          ) : (
            <>
              나머지 {visibleColumns.length - 3}개 펼쳐보기
              <ChevronDown aria-hidden="true" size={14} />
            </>
          )}
        </button>
      )}
    </section>
  )
}

interface ViewButtonProps {
  active: boolean
  children: React.ReactNode
  onClick: () => void
}

const ViewButton = ({ active, children, onClick }: ViewButtonProps) => (
  <button
    className={`rounded-md px-2.5 py-1.5 transition ${
      active ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
    }`}
    onClick={onClick}
    type="button"
  >
    {children}
  </button>
)

export default SheetColumnSchema
