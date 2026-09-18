import { useQuery } from '@tanstack/react-query'
import { CalendarClock, FileCheck2, ShieldCheck } from 'lucide-react'
import { useParams } from 'react-router-dom'

import { getAnalysisPublicShare } from '@/api/analysis/publicShareApi'
import AdvancedAnalysisSection from '@/components/analysis/result/AdvancedAnalysisSection'
import AnalysisResultSummary from '@/components/analysis/result/AnalysisResultSummary'
import InsightReportSection from '@/components/analysis/result/InsightReportSection'
import WorkbookExplorer from '@/components/analysis/workbook/explorer/WorkbookExplorer'
import WorkbookSemanticOverview from '@/components/analysis/workbook/semantic/summaries/WorkbookSemanticOverview'
import BistelligenceLogo from '@/components/navigation/brand/BistelligenceLogo'
import {
  PublicShareErrorState,
  PublicShareLoadingState,
} from '@/pages/analysis/shared/PublicShareStates'
import { usePublicShareMetadata } from '@/pages/analysis/shared/usePublicShareMetadata'

const SharedAnalysisPage = () => {
  const { token = '' } = useParams<{ token: string }>()
  const share = useQuery({
    queryKey: ['analysis-public-share', token],
    queryFn: () => getAnalysisPublicShare(token),
    enabled: token.length > 0,
    retry: false,
  })

  usePublicShareMetadata()

  return (
    <main className="min-h-dvh bg-app-background px-4 py-5 text-slate-900 md:px-8 md:py-9">
      <div className="mx-auto w-full max-w-[1380px]">
        <header className="mb-5 flex items-center justify-between gap-4 rounded-2xl border border-slate-200/70 bg-white px-5 py-4 shadow-panel">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-600 text-white shadow-brand">
              <FileCheck2 aria-hidden="true" size={20} />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-extrabold tracking-tight text-slate-950">
                Excel 분석 공유 보고서
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                초대받은 텔레그램 수신자에게 제공된 읽기 전용 결과입니다.
              </p>
            </div>
          </div>
          <div className="hidden w-36 shrink-0 sm:block">
            <BistelligenceLogo />
          </div>
        </header>

        {share.isPending && <PublicShareLoadingState />}
        {share.isError && (
          <PublicShareErrorState
            error={share.error}
            onRetry={() => void share.refetch()}
          />
        )}
        {share.data && <SharedResult result={share.data} />}
      </div>
    </main>
  )
}

const SharedResult = ({
  result,
}: {
  result: Awaited<ReturnType<typeof getAnalysisPublicShare>>
}) => (
  <section className="panel p-5 md:p-7">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-emerald-600">
          <ShieldCheck aria-hidden="true" size={18} />
          <span className="text-xs font-extrabold tracking-wide">읽기 전용 공유</span>
        </div>
        <h1 className="mt-2 break-words text-xl font-extrabold tracking-tight text-slate-950 md:text-2xl">
          {result.workbook.filename}
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          원본 Excel은 제공되지 않으며 이 페이지에서는 분석 결과만 확인할 수 있습니다.
        </p>
      </div>
      <div className="space-y-2 text-xs font-semibold text-slate-500">
        <time
          className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2.5"
          dateTime={result.createdAt}
        >
          <CalendarClock aria-hidden="true" size={15} />
          분석 {new Date(result.createdAt).toLocaleString('ko-KR')}
        </time>
        <time
          className="flex items-center gap-2 rounded-xl bg-amber-50 px-3 py-2.5 text-amber-700"
          dateTime={result.expiresAt}
        >
          <CalendarClock aria-hidden="true" size={15} />
          만료 {new Date(result.expiresAt).toLocaleString('ko-KR')}
        </time>
      </div>
    </div>

    <AnalysisResultSummary workbook={result.workbook} />

    {result.insightReport && <InsightReportSection report={result.insightReport} />}

    <AdvancedAnalysisSection>
      <WorkbookSemanticOverview
        excludedSheets={result.workbook.excludedSheets ?? []}
        sheets={result.workbook.sheets}
      />
      <WorkbookExplorer sheets={result.workbook.sheets} />
    </AdvancedAnalysisSection>
  </section>
)

export default SharedAnalysisPage
