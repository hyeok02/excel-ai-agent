import { useMemo, useState } from 'react'

import type { SheetResult } from '@/api/analysis'
import SheetResultCard from '@/components/analysis/workbook/explorer/SheetResultCard'
import { SheetRoleBadge } from '@/components/analysis/workbook/semantic/components/ClassificationBadges'
import { getSheetSemanticMetadata } from '@/components/analysis/workbook/semantic/semanticModel'

interface WorkbookExplorerProps {
  sheets: SheetResult[]
}

const ROLE_PRIORITY = {
  output: 5,
  input: 4,
  calculation: 3,
  documentation: 2,
  system: 1,
} as const

const defaultSheet = (sheets: SheetResult[]) =>
  sheets.reduce<SheetResult | undefined>((best, sheet) => {
    if (!best) return sheet
    const candidate = getSheetSemanticMetadata(sheet).classification
    const current = getSheetSemanticMetadata(best).classification
    const candidateRole = candidate ? ROLE_PRIORITY[candidate.role] : 0
    const currentRole = current ? ROLE_PRIORITY[current.role] : 0
    if (candidateRole !== currentRole) return candidateRole > currentRole ? sheet : best
    return (candidate?.importanceScore ?? 0) > (current?.importanceScore ?? 0)
      ? sheet
      : best
  }, undefined)

const WorkbookExplorer = ({ sheets }: WorkbookExplorerProps) => {
  const preferredSheet = useMemo(() => defaultSheet(sheets), [sheets])
  const [selectedSheetName, setSelectedSheetName] = useState(
    () => preferredSheet?.name ?? '',
  )
  const selectedSheet = useMemo(
    () => sheets.find((sheet) => sheet.name === selectedSheetName) ?? preferredSheet,
    [preferredSheet, selectedSheetName, sheets],
  )

  if (!selectedSheet) return null

  return (
    <section className="mt-6">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold tracking-[0.16em] text-brand-600">
            워크북 탐색
          </p>
          <h2 className="mt-1 text-lg font-extrabold text-slate-900">시트별 핵심 내용</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            시트를 선택하면 이 시트가 하는 일과 주요 원본 내용을 먼저 보여줍니다.
          </p>
        </div>
        <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">
          전체 {sheets.length}개 시트
        </span>
      </div>

      <div
        aria-label="Excel 시트 선택"
        className="mb-3 flex gap-2 overflow-x-auto rounded-2xl bg-slate-50 p-2"
        role="tablist"
      >
        {sheets.map((sheet) => {
          const selected = sheet.name === selectedSheet.name
          const { classification } = getSheetSemanticMetadata(sheet)
          return (
            <button
              aria-selected={selected}
              className={`shrink-0 rounded-xl px-4 py-2.5 text-left text-xs font-bold transition ${
                selected
                  ? 'bg-white text-brand-700 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-500 hover:bg-white/70 hover:text-slate-700'
              }`}
              key={sheet.name}
              onClick={() => setSelectedSheetName(sheet.name)}
              role="tab"
              type="button"
            >
              <span className="flex items-center gap-2">
                <span>{sheet.name}</span>
                {classification && <SheetRoleBadge role={classification.role} />}
                <span className="font-medium text-slate-400">
                  {sheet.rows.toLocaleString()}×{sheet.columns.toLocaleString()}
                </span>
              </span>
            </button>
          )
        })}
      </div>

      <SheetResultCard key={selectedSheet.name} sheet={selectedSheet} />
    </section>
  )
}

export default WorkbookExplorer
