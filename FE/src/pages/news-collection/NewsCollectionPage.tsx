import SummaryCards from '@/components/common/SummaryCards'

const NewsCollectionPage = () => {
  return (
    <div className="space-y-6">
      <section className="panel flex flex-wrap items-start justify-between gap-4 p-6 md:p-8">
        <div>
          <p className="eyebrow">NEWS COLLECTION</p>
          <h1 className="page-title">뉴스 수집</h1>
          <p className="page-description">
            검색 키워드별 뉴스 수집 현황과 수집 기사, 텔레그램 발송 이력을 확인하는
            화면입니다.
          </p>
        </div>
      </section>

      <SummaryCards
        items={[
          { label: '활성 키워드', value: '0', helper: '자동 수집 주제' },
          { label: '오늘 수집', value: '0', helper: '수집된 기사 수' },
          { label: '발송 성공', value: '0', helper: '최근 텔레그램 발송' },
        ]}
      />

      <section className="grid gap-6 xl:grid-cols-[20rem_1fr]">
        <article className="panel p-5">
          <div className="flex items-center justify-between">
            <h2 className="section-title">키워드 목록</h2>
            <span className="text-xs text-slate-400">Live Feed</span>
          </div>
          <div className="empty-state mt-5 min-h-64">
            <span className="empty-state-icon">KW</span>
            <p className="font-semibold text-slate-700">활성 키워드가 없습니다.</p>
            <p className="text-sm text-slate-500">뉴스 수집 API 연결 후 표시됩니다.</p>
          </div>
        </article>

        <article className="panel p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">키워드 수집 현황</h2>
            <span className="text-xs text-slate-400">Latest</span>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5">
              <p className="text-sm text-slate-500">수집된 기사</p>
              <p className="mt-3 text-2xl font-bold text-slate-400">0건</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-5">
              <p className="text-sm text-slate-500">발송 구독</p>
              <p className="mt-3 text-2xl font-bold text-slate-400">0건</p>
            </div>
          </div>
          <div className="empty-state mt-4 min-h-32">
            <p className="font-semibold text-slate-700">최근 수집 기사가 없습니다.</p>
            <p className="text-sm text-slate-500">
              키워드를 선택하면 기사와 발송 이력이 표시됩니다.
            </p>
          </div>
        </article>
      </section>
    </div>
  )
}

export default NewsCollectionPage
