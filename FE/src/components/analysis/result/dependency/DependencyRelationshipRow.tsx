import { ArrowRight } from 'lucide-react'

import {
  parseCellLabel,
  type RelationshipGroup,
  shortLocation,
} from '@/components/analysis/result/dependency/dependencyMapUtils'

interface DependencyRelationshipRowProps {
  relationship: RelationshipGroup
}

const DependencyRelationshipRow = ({ relationship }: DependencyRelationshipRowProps) => {
  const targetCell = parseCellLabel(relationship.targetLabel)
  const sharedSheet =
    targetCell &&
    relationship.sourceLabels.every(
      (label) => parseCellLabel(label)?.sheet === targetCell.sheet,
    )
      ? targetCell.sheet
      : undefined
  const visibleSources = relationship.sourceLabels.slice(0, 3)
  const sourceText = visibleSources
    .map((label) => shortLocation(label, sharedSheet))
    .join(', ')
  const hiddenSourceCount = relationship.sourceLabels.length - visibleSources.length
  const targetText = shortLocation(relationship.targetLabel, sharedSheet)

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="grid items-center gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.12em] text-slate-400">
            입력·참조 범위
          </p>
          <code
            className="mt-1 block truncate text-xs font-bold text-slate-700"
            title={sourceText}
          >
            {sourceText}
            {hiddenSourceCount > 0 ? ` 외 ${hiddenSourceCount}개 범위` : ''}
          </code>
        </div>
        <span className="grid size-8 place-items-center rounded-full bg-brand-50 text-brand-600">
          <ArrowRight aria-hidden="true" size={15} />
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.12em] text-slate-400">
            계산 결과 셀
          </p>
          <code
            className="mt-1 block truncate text-xs font-extrabold text-slate-900"
            title={targetText}
          >
            {targetText}
          </code>
        </div>
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-500">
        {sharedSheet ? `${sharedSheet} 시트에서 ` : ''}
        <strong className="font-bold text-slate-700">{sourceText}</strong>의 값이 바뀌면{' '}
        <strong className="font-bold text-slate-900">{targetText}</strong> 계산 결과가
        영향을 받을 수 있어요.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {relationship.crossSheet && (
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-[10px] font-bold text-brand-700">
            다른 시트 참조
          </span>
        )}
        {relationship.sourceCount > 1 && (
          <span className="rounded-lg bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
            {relationship.sourceCount.toLocaleString()}개 셀 참조
          </span>
        )}
      </div>

      {relationship.target?.formula && (
        <details className="mt-3 rounded-xl bg-slate-50 px-3 py-2">
          <summary className="cursor-pointer list-none text-[11px] font-bold text-slate-500 marker:hidden">
            실제 수식 보기
          </summary>
          <code className="mt-2 block break-all text-[11px] leading-5 text-slate-600">
            {relationship.target.formula}
          </code>
        </details>
      )}
    </div>
  )
}

export default DependencyRelationshipRow
