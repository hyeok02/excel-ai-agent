import { ChartNoAxesCombined } from 'lucide-react'

import type { CellValue, ChartResult } from '@/api/analysis'
import ChartVisualPreview from '@/components/analysis/workbook/ChartVisualPreview'
import OriginalLocationButton from '@/components/analysis/workbook/OriginalLocationButton'

interface SheetChartDetailsProps {
  charts: ChartResult[]
  sheetName: string
}

const formatSamples = (values: CellValue[]) => {
  if (values.length === 0) return '표본 없음'
  return values.map((value) => (value === null ? '—' : String(value))).join(', ')
}

const SheetChartDetails = ({ charts, sheetName }: SheetChartDetailsProps) => {
  if (charts.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ChartNoAxesCombined aria-hidden="true" className="text-brand-600" size={16} />
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            차트와 데이터 계열
          </h4>
        </div>
        <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-[11px] font-bold text-brand-700">
          {charts.length}개
        </span>
      </div>

      <div className="mt-3 space-y-3">
        {charts.map((chart, chartIndex) => (
          <details
            className="rounded-xl bg-slate-50/80"
            key={`${chart.anchorCell}-${chartIndex}`}
            open={chartIndex === 0}
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 marker:hidden">
              <div>
                <p className="text-sm font-extrabold text-slate-800">
                  {chart.title || `제목 없는 ${chart.chartType}`}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {chart.chartType} · 배치 {chart.anchorCell || '확인 불가'} · 계열{' '}
                  {chart.seriesCount}개
                </p>
              </div>
            </summary>

            <div className="space-y-2 border-t border-slate-200 p-3">
              <div className="flex justify-end">
                {chart.anchorCell && (
                  <OriginalLocationButton location={chart.anchorCell} sheetName={sheetName} />
                )}
              </div>
              <ChartVisualPreview chart={chart} />
              {(chart.series ?? []).map((series, seriesIndex) => (
                <div className="rounded-xl bg-white p-3 text-xs" key={seriesIndex}>
                  <p className="font-extrabold text-slate-700">
                    {series.title || `계열 ${seriesIndex + 1}`}
                  </p>
                  <dl className="mt-2 grid gap-2 text-slate-500">
                    <div>
                      <dt className="font-bold text-slate-400">범주 참조</dt>
                      <dd className="mt-0.5 break-all">
                        {series.categoriesReference || '없음'}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-bold text-slate-400">값 참조</dt>
                      <dd className="mt-0.5 break-all">{series.valuesReference || '없음'}</dd>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div>
                        <dt className="font-bold text-slate-400">범주 표본</dt>
                        <dd className="mt-0.5 break-all">
                          {formatSamples(series.categorySamples ?? [])}
                        </dd>
                      </div>
                      <div>
                        <dt className="font-bold text-slate-400">값 표본</dt>
                        <dd className="mt-0.5 break-all">
                          {formatSamples(series.valueSamples ?? [])}
                        </dd>
                      </div>
                    </div>
                  </dl>
                </div>
              ))}
              {chart.truncated && (
                <p className="text-[11px] text-slate-400">
                  계열이 많아 앞쪽 12개만 표시합니다.
                </p>
              )}
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}

export default SheetChartDetails
