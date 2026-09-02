import WorkspaceOverviewPage from '@/components/workspace/WorkspaceOverviewPage'

const SUMMARY_ITEMS = [
  { label: '등록 인물', value: '0', helper: '추적 대상 전체' },
  { label: '신규 기사', value: '0', helper: '최근 수집 결과' },
  { label: '텔레그램 발송', value: '0', helper: '활성 수신 대상' },
]

const PersonNewsPage = () => {
  return (
    <WorkspaceOverviewPage
      description="추적 대상 인물의 최신 기사를 수집하고 LLM 종합 판단, 감성 톤, 근거 기사와 분석 이력을 확인하는 화면입니다."
      eyebrow="PEOPLE NEWS TRACKING"
      summaryItems={SUMMARY_ITEMS}
      title="인물 뉴스 추적"
    >
      <section className="grid gap-6 xl:grid-cols-[20rem_1fr]">
        <article className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="section-title">추적 인물</h2>
            <span className="text-xs text-slate-400">Watchlist</span>
          </div>
          <div className="empty-state mt-5 min-h-64">
            <span className="empty-state-icon">PE</span>
            <p className="font-semibold text-slate-700">등록된 인물이 없습니다.</p>
            <p className="text-sm text-slate-500">인물 마스터 API 연결 후 표시됩니다.</p>
          </div>
        </article>

        <article className="panel p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">LLM 분석 결과</h2>
            <span className="text-xs text-slate-400">
              종합 판단 · 감성 톤 · 근거 기사
            </span>
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-[1fr_12rem]">
            <div className="min-h-48 rounded-xl border border-slate-200 bg-slate-50/60 p-5">
              <p className="text-sm font-semibold text-slate-700">종합 판단</p>
              <p className="mt-4 text-sm leading-6 text-slate-400">
                추적 인물을 선택하면 최신 기사 기반 분석이 표시됩니다.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">감성 톤</p>
              <p className="mt-3 text-xl font-bold text-slate-400">—</p>
            </div>
          </div>
        </article>
      </section>
    </WorkspaceOverviewPage>
  )
}

export default PersonNewsPage
