import { ChevronDown, Grid3X3 } from 'lucide-react'
import { useMemo, useState } from 'react'

import type { RegionResult } from '@/api/analysis'
import HeaderPathList from '@/components/analysis/workbook/details/HeaderPathList'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'
import {
  regionSizeLabel,
  safeRegionCount,
} from '@/components/analysis/workbook/details/regionDetailsUtils'
import CellPreviewTable from '@/components/analysis/workbook/previews/CellPreviewTable'
import RegionSemanticSummary, {
  RegionSemanticBadges,
} from '@/components/analysis/workbook/semantic/summaries/RegionSemanticSummary'

interface SheetRegionDetailsProps {
  regions: RegionResult[]
  sheetName: string
}

const INITIAL_REGION_COUNT = 5

const SheetRegionDetails = ({ regions, sheetName }: SheetRegionDetailsProps) => {
  const [showAll, setShowAll] = useState(false)
  const prioritizedRegions = useMemo(
    () =>
      regions
        .map((region, originalIndex) => ({ region, originalIndex }))
        .sort((left, right) => {
          const sizeDifference =
            (safeRegionCount(right.region.cellCount) ?? 0) -
            (safeRegionCount(left.region.cellCount) ?? 0)
          return sizeDifference || left.originalIndex - right.originalIndex
        }),
    [regions],
  )
  const visibleRegions = showAll
    ? prioritizedRegions
    : prioritizedRegions.slice(0, INITIAL_REGION_COUNT)
  const hiddenRegionCount = Math.max(0, regions.length - INITIAL_REGION_COUNT)

  if (regions.length === 0) return null

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

      <div className="mt-3 space-y-2">
        {visibleRegions.map(({ region, originalIndex }) => (
          <details
            className="group rounded-xl border border-slate-200 bg-white"
            key={`${region.startCell}-${region.endCell}-${originalIndex}`}
          >
            <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-4 py-3 marker:hidden">
              <div className="min-w-0">
                <span className="font-bold text-slate-700">
                  {region.title || `데이터 영역 ${originalIndex + 1}`}
                </span>
                <p className="mt-1 text-[11px] text-slate-400">
                  {region.startCell}:{region.endCell} · {regionSizeLabel(region)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <RegionSemanticBadges region={region} />
                <ChevronDown
                  aria-hidden="true"
                  className="text-slate-300 transition-transform group-open:rotate-180"
                  size={16}
                />
              </div>
            </summary>
            <div className="border-t border-slate-100 p-3">
              <RegionSemanticSummary region={region} />
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

              <HeaderPathList paths={region.headerPaths ?? []} />
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
            {showAll ? '주요 영역만 보기' : `나머지 ${hiddenRegionCount}개 영역 펼쳐보기`}
            <ChevronDown
              aria-hidden="true"
              className={`transition-transform ${showAll ? 'rotate-180' : ''}`}
              size={15}
            />
          </button>
        )}
      </div>
    </section>
  )
}

export default SheetRegionDetails
