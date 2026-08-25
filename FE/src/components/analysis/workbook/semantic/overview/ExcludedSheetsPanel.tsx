import type { ExcludedSheetResult } from '@/api/analysis'
import {
  AnalysisDecisionBadge,
  ImportanceBadge,
  SheetRoleBadge,
} from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import { getSheetSemanticMetadata } from '@/components/analysis/workbook/semantic/semanticModel'

const ExcludedSheetCard = ({ sheet }: { sheet: ExcludedSheetResult }) => {
  const { analysisInclusion, classification } = getSheetSemanticMetadata(sheet)

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-extrabold text-slate-700">{sheet.name}</p>
        <div className="flex flex-wrap gap-1.5">
          {classification && (
            <>
              <SheetRoleBadge role={classification.role} />
              <ImportanceBadge importance={classification.importance} />
            </>
          )}
          {analysisInclusion && (
            <AnalysisDecisionBadge decision={analysisInclusion.decision} />
          )}
        </div>
      </div>
      <p className="mt-2 text-[11px] leading-5 text-slate-500">
        {analysisInclusion?.reason ?? '제외 사유가 제공되지 않았습니다.'}
      </p>
      <p className="mt-1 text-[9px] font-bold text-slate-300">
        {analysisInclusion?.reasonCode ?? 'REASON_NOT_PROVIDED'} · {sheet.state}
      </p>
    </article>
  )
}

const ExcludedSheetsPanel = ({ sheets }: { sheets: ExcludedSheetResult[] }) => {
  if (sheets.length === 0) return null

  return (
    <details className="border-t border-slate-100">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3 px-5 py-4 marker:hidden md:px-6">
        <div>
          <p className="text-xs font-extrabold text-slate-700">분석 제외 시트</p>
          <p className="mt-1 text-[11px] text-slate-400">
            숨김·애드인·캐시 시트를 분석 입력에서 제외했어요.
          </p>
        </div>
        <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-[11px] font-bold text-slate-600">
          {sheets.length}개 보기
        </span>
      </summary>
      <div className="grid gap-2 border-t border-slate-100 bg-slate-50/70 p-4 md:grid-cols-2 md:p-5">
        {sheets.map((sheet) => (
          <ExcludedSheetCard key={sheet.name} sheet={sheet} />
        ))}
      </div>
    </details>
  )
}

export default ExcludedSheetsPanel
