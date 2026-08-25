import { ChevronDown, Grid3X3 } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { RegionResult } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/common/OriginalLocationButton'
import CellPreviewTable from '@/components/analysis/workbook/previews/CellPreviewTable'

interface SheetRegionDetailsProps {
  regions: RegionResult[]
  sheetName: string
}

const INITIAL_REGION_COUNT = 5

const safeCount = (value: number | undefined | null) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

const regionSizeLabel = (region: RegionResult) => {
  const rows = safeCount(region.rowCount)
  const columns = safeCount(region.columnCount)
  const cells =
    safeCount(region.cellCount) ??
    (rows !== null && columns !== null ? rows * columns : null)
  const dimensions =
    rows !== null && columns !== null ? `${rows}행 × ${columns}열` : '크기 정보 없음'
  const cellCount = cells !== null ? ` · ${cells.toLocaleString()}셀` : ''

  return `${dimensions}${cellCount}`
}

const SheetRegionDetails = ({ regions, sheetName }: SheetRegionDetailsProps) => {
  const [showAll, setShowAll] = useState(false)
  const prioritizedRegions = useMemo(
    () =>
      regions
        .map((region, originalIndex) => ({ region, originalIndex }))
        .sort((left, right) => {
          const sizeDifference =
            (safeCount(right.region.cellCount) ?? 0) -
            (safeCount(left.region.cellCount) ?? 0)
          return sizeDifference || left.originalIndex - right.originalIndex
        }),
    [regions],
  )
  const visibleRegions = showAll
    ? prioritizedRegions
    : prioritizedRegions.slice(0, INITIAL_REGION_COUNT)
  const hiddenRegionCount = Math.max(0, regions.length - INITIAL_REGION_COUNT)

  return (
    <section className="rounded-2xl bg-slate-50/80 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Grid3X3 aria-hidden="true" className="text-brand-600" size={16} />
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            데이터 영역과 셀 미리보기
          </h4>
        </div>
        {regions.length > INITIAL_REGION_COUNT && (
          <span className="rounded-lg bg-white px-2.5 py-1 text-[10px] font-bold text-slate-400">
            주요 {INITIAL_REGION_COUNT}개 우선 표시 · 전체 {regions.length}개
          </span>
        )}
      </div>

      {regions.length > 0 ? (
        <div className="mt-3 space-y-2">
          {visibleRegions.map(({ region, originalIndex }, visibleIndex) => (
            <details
              className="group rounded-xl border border-slate-200 bg-white"
              key={`${region.startCell}-${region.endCell}-${originalIndex}`}
              open={visibleIndex === 0}
            >
              <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 marker:hidden">
                <div>
                  <span className="font-bold text-slate-700">
                    {region.title || `데이터 영역 ${originalIndex + 1}`}
                  </span>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {region.startCell}:{region.endCell} · {regionSizeLabel(region)}
                  </p>
                </div>
                <ChevronDown
                  aria-hidden="true"
                  className="text-slate-300 transition-transform group-open:rotate-180"
                  size={16}
                />
              </summary>
              <div className="border-t border-slate-100 p-3">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <OriginalLocationButton
                    location={`${region.startCell}:${region.endCell}`}
                    sheetName={sheetName}
                  />
                  {(region.mergedRanges ?? []).length > 0 && (
                    <span className="rounded-lg bg-amber-50 px-2.5 py-1.5 text-[11px] font-bold text-amber-700">
                      병합 셀 {region.mergedRanges.length}개
                    </span>
                  )}
                </div>

                {(region.headerPaths ?? []).length > 0 && (
                  <div className="mb-3 rounded-xl bg-slate-50 p-3">
                    <p className="text-[11px] font-extrabold text-slate-500">헤더 구조</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {region.headerPaths.slice(0, 12).map((path) => (
                        <span
                          className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] text-slate-600"
                          key={`${path.column}-${path.labels.join('-')}`}
                        >
                          <b className="text-slate-400">{path.column}</b>{' '}
                          {path.labels.join(' › ')}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <CellPreviewTable rows={region.previewRows ?? []} />
                {region.truncated && (
                  <p className="mt-2 text-[11px] text-slate-400">
                    큰 영역은 앞쪽 8행 × 8열만 표시합니다.
                  </p>
                )}
              </div>
            </details>
          ))}
          {hiddenRegionCount > 0 && (
            <button
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white px-4 py-3 text-xs font-bold text-slate-500 transition hover:border-brand-300 hover:text-brand-700"
              onClick={() => setShowAll((current) => !current)}
              type="button"
            >
              {showAll
                ? '주요 영역만 보기'
                : `나머지 ${hiddenRegionCount}개 영역 펼쳐보기`}
              <ChevronDown
                aria-hidden="true"
                className={`transition-transform ${showAll ? 'rotate-180' : ''}`}
                size={15}
              />
            </button>
          )}
        </div>
      ) : (
        <p className="mt-3 rounded-xl bg-white p-4 text-xs text-slate-400">
          탐지된 데이터 영역이 없습니다.
        </p>
      )}
    </section>
  )
}

export default SheetRegionDetails
