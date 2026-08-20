import { CalendarClock, CheckCircle2, Network, Sparkles } from 'lucide-react'

import type { AnalysisMode, AnalysisResultDetails, WorkbookResult } from '@/api/analysis'
import AgentReadySection from '@/components/analysis/result/AgentReadySection'
import AnalysisExportActions from '@/components/analysis/result/AnalysisExportActions'
import DependencyMapSection from '@/components/analysis/result/DependencyMapSection'
import InsightReportSection from '@/components/analysis/result/InsightReportSection'
import WorkbookExplorer from '@/components/analysis/workbook/WorkbookExplorer'

interface AnalysisResultSectionProps {
  mode: AnalysisMode
  result: AnalysisResultDetails
}

const getWorkbookTotals = (workbook: WorkbookResult) => {
  return workbook.sheets.reduce(
    (totals, sheet) => ({
      regions: totals.regions + sheet.regionCount,
      formulas: totals.formulas + sheet.formulaCount,
      tables: totals.tables + sheet.tableCount,
      charts: totals.charts + sheet.chartCount,
    }),
    { regions: 0, formulas: 0, tables: 0, charts: 0 },
  )
}

const MODE_PRESENTATION = {
  BFS: {
    badge: 'BFS 군집 분석',
    completion: '군집 분석 완료',
    icon: Network,
  },
  LLM: {
    badge: 'LLM 직접 분석',
    completion: 'AI 분석 완료',
    icon: Sparkles,
  },
} as const

const AnalysisResultSection = ({ mode, result }: AnalysisResultSectionProps) => {
  const { workbook } = result
  const modePresentation = MODE_PRESENTATION[mode]
  const ModeIcon = modePresentation.icon
  const totals = getWorkbookTotals(workbook)
  const summaryItems = [
    ['시트', workbook.sheetCount],
    ['데이터 영역', totals.regions],
    ['수식', totals.formulas],
    ['테이블', totals.tables],
    ['차트', totals.charts],
  ] as const

  return (
    <section className="panel p-5 md:p-7" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-emerald-600">
            <CheckCircle2 aria-hidden="true" size={18} />
            <span className="text-xs font-extrabold tracking-wide">
              {modePresentation.completion}
            </span>
          </div>
          <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
            {workbook.filename}
          </h2>
          <p className="mt-1 text-sm text-slate-500">분석 ID {result.analysisId}</p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          <span className="inline-flex h-10 items-center gap-2 rounded-xl bg-brand-50 px-3 text-xs font-bold text-brand-700">
            <ModeIcon aria-hidden="true" size={15} />
            {modePresentation.badge}
          </span>
          <time
            className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-50 px-3 text-xs font-semibold text-slate-500"
            dateTime={result.createdAt}
          >
            <CalendarClock aria-hidden="true" size={15} />
            {new Date(result.createdAt).toLocaleString('ko-KR')}
          </time>
          <AnalysisExportActions result={result} />
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {summaryItems.map(([label, value]) => (
          <div className="rounded-2xl bg-slate-50 p-4" key={label}>
            <p className="text-xs font-semibold text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
              {value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {mode === 'LLM' && result.insightReport && (
        <InsightReportSection report={result.insightReport} />
      )}

      {workbook.dependencyGraph && workbook.dependencyGraph.nodeCount > 0 && (
        <DependencyMapSection graph={workbook.dependencyGraph} mode={mode} />
      )}

      {mode === 'BFS' &&
        (!workbook.dependencyGraph || workbook.dependencyGraph.nodeCount === 0) && (
          <section className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 px-5 py-8 text-center">
            <Network aria-hidden="true" className="mx-auto text-slate-400" size={24} />
            <h3 className="mt-3 text-base font-extrabold text-slate-900">
              연결된 수식 군집이 없습니다
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              셀 간 참조 관계가 없거나 각 수식이 독립적으로 구성된 워크북이에요.
            </p>
          </section>
        )}

      <WorkbookExplorer sheets={workbook.sheets} />

      <AgentReadySection hasInsightReport={result.insightReport !== null} />
    </section>
  )
}

export default AnalysisResultSection
