import { Grid3X3 } from 'lucide-react'

import type { RegionResult } from '@/api/analysis'
import CellPreviewTable from '@/components/analysis/CellPreviewTable'

interface SheetRegionDetailsProps {
  regions: RegionResult[]
}

const SheetRegionDetails = ({ regions }: SheetRegionDetailsProps) => {
  return (
    <section className="rounded-2xl bg-slate-50/80 p-4">
      <div className="flex items-center gap-2">
        <Grid3X3 aria-hidden="true" className="text-brand-600" size={16} />
        <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
          데이터 영역과 셀 미리보기
        </h4>
      </div>

      {regions.length > 0 ? (
        <div className="mt-3 space-y-2">
          {regions.map((region, index) => (
            <details
              className="group rounded-xl border border-slate-200 bg-white"
              key={`${region.startCell}-${region.endCell}-${index}`}
              open={index === 0}
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 marker:hidden">
                <span className="font-bold text-slate-700">
                  {region.startCell} : {region.endCell}
                </span>
                <span className="text-xs text-slate-400">
                  {region.cellCount.toLocaleString()}셀
                </span>
              </summary>
              <div className="border-t border-slate-100 p-3">
                <CellPreviewTable rows={region.previewRows ?? []} />
                {region.truncated && (
                  <p className="mt-2 text-[11px] text-slate-400">
                    큰 영역은 앞쪽 8행 × 8열만 표시합니다.
                  </p>
                )}
              </div>
            </details>
          ))}
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
