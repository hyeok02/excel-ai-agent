import { Eye } from 'lucide-react'

import type { RegionResult, SheetResult } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'
import { safeRegionCount } from '@/components/analysis/workbook/details/regionDetailsUtils'
import CellPreviewTable from '@/components/analysis/workbook/previews/CellPreviewTable'
import { SheetRoleBadge } from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import { getSheetSemanticMetadata } from '@/components/analysis/workbook/semantic/semanticModel'
import { SHEET_ROLE_PRESENTATION } from '@/components/analysis/workbook/semantic/sheetRolePresentation'

const primaryRegion = (regions: RegionResult[]) =>
  regions.reduce<RegionResult | null>((largest, region) => {
    if (!largest) return region
    const currentSize = safeRegionCount(region.cellCount) ?? 0
    const largestSize = safeRegionCount(largest.cellCount) ?? 0
    return currentSize > largestSize ? region : largest
  }, null)

const SheetAtAGlance = ({ sheet }: { sheet: SheetResult }) => {
  const { classification } = getSheetSemanticMetadata(sheet)
  const presentation = classification
    ? SHEET_ROLE_PRESENTATION[classification.role]
    : null
  const region = primaryRegion(sheet.regions ?? [])
  const previewRows = (region?.previewRows ?? []).slice(0, 5)

  return (
    <section className="border-t border-slate-100 px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl bg-brand-50/50 p-4">
        <div>
          <p className="text-[10px] font-extrabold tracking-[0.14em] text-brand-600">
            이 시트가 하는 일
          </p>
          <p className="mt-1 text-sm font-extrabold leading-6 text-slate-800">
            {presentation?.description ??
              '시트의 주요 데이터와 구조를 확인할 수 있습니다.'}
          </p>
        </div>
        {classification && <SheetRoleBadge role={classification.role} />}
      </div>

      {region && previewRows.length > 0 && (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="flex items-center gap-2 text-xs font-extrabold text-slate-700">
                <Eye aria-hidden="true" className="text-brand-600" size={15} />
                원본 내용 미리보기
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                {region.title || '가장 큰 데이터 영역'} · {region.startCell}:
                {region.endCell}
              </p>
            </div>
            <OriginalLocationButton
              location={`${region.startCell}:${region.endCell}`}
              sheetName={sheet.name}
            />
          </div>
          <CellPreviewTable compact rows={previewRows} />
          {(region.previewRows?.length ?? 0) > previewRows.length && (
            <p className="mt-2 text-[11px] text-slate-400">
              앞쪽 5행만 보여줍니다. 전체 내용은 상세 분석에서 확인할 수 있어요.
            </p>
          )}
        </div>
      )}
    </section>
  )
}

export default SheetAtAGlance
