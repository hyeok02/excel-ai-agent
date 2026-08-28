import { Boxes } from 'lucide-react'

import { parseCellLabel } from '@/components/analysis/result/dependency/dependencyMapUtils'
import FormulaDisclosure from '@/components/analysis/result/dependency/FormulaDisclosure'
import type { RelationshipPattern } from '@/components/analysis/result/dependency/relationshipPatterns'

interface RelationshipPatternCardProps {
  pattern: RelationshipPattern
  sheetName: string
}

const compactLocation = (label: string) => {
  const parsed = parseCellLabel(label)
  return parsed ? `${parsed.sheet}!${parsed.column}${parsed.row}` : label
}

const RelationshipPatternCard = ({
  pattern,
  sheetName,
}: RelationshipPatternCardProps) => {
  const { relationships } = pattern
  const targetLocations = relationships.map(({ targetLabel }) =>
    compactLocation(targetLabel),
  )
  const crossSheetCount = relationships.filter(({ crossSheet }) => crossSheet).length
  const representativeFormula = relationships.find(({ target }) => target?.formula)
    ?.target?.formula

  return (
    <article className="self-start rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <Boxes aria-hidden="true" size={16} />
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.12em] text-brand-600">
            {sheetName} 시트 · 계산 방식
          </p>
          <h5 className="mt-1 text-sm font-extrabold leading-6 text-slate-900">
            {pattern.meaning}
          </h5>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            서로 떨어진 셀도 같은 목적의 수식이면 하나로 묶었습니다. 이 방식으로{' '}
            {relationships.length.toLocaleString()}개 결과값을 자동으로 채웁니다.
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-lg bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
          결과 {relationships.length.toLocaleString()}곳
        </span>
        {crossSheetCount > 0 && (
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-[10px] font-bold text-brand-700">
            다른 시트 참조 {crossSheetCount.toLocaleString()}곳
          </span>
        )}
      </div>

      <details className="mt-3 border-t border-slate-100 pt-3">
        <summary className="cursor-pointer list-none text-[11px] font-bold text-slate-500 marker:hidden">
          검증 정보 보기
        </summary>
        <div className="mt-3 rounded-xl bg-slate-50 p-3">
          <p className="text-[10px] font-bold text-slate-400">결과가 입력되는 위치</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {targetLocations.slice(0, 8).map((location) => (
              <span
                className="rounded-lg bg-white px-2 py-1 text-[11px] text-slate-600"
                key={location}
              >
                <code>{location}</code>
              </span>
            ))}
            {targetLocations.length > 8 && (
              <span className="text-[11px] text-slate-400">
                외 {(targetLocations.length - 8).toLocaleString()}곳
              </span>
            )}
          </div>
        </div>
        {representativeFormula && <FormulaDisclosure formula={representativeFormula} />}
      </details>
    </article>
  )
}

export default RelationshipPatternCard
