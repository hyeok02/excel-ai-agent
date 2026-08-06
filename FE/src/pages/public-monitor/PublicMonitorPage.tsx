import SummaryCards from '@/components/common/SummaryCards'

const PublicMonitorPage = () => {
  return (
    <div className="space-y-6">
      <section className="panel flex flex-wrap items-start justify-between gap-4 p-6 md:p-8">
        <div>
          <p className="eyebrow">PUBLIC INSTITUTION MONITOR</p>
          <h1 className="page-title">공공기관 모니터</h1>
          <p className="page-description">
            등록한 공공기관 게시판을 주기적으로 확인하고, 신규 게시물을 수집·요약하는
            화면입니다.
          </p>
        </div>
      </section>

      <SummaryCards
        items={[
          { label: '활성 소스', value: '0', helper: '등록된 기관 게시판' },
          { label: '최근 감지', value: '0', helper: '신규 게시물' },
          { label: '경고', value: '0', helper: '확인이 필요한 항목' },
        ]}
      />

      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5">
          <div>
            <h2 className="section-title">실행 제어</h2>
            <p className="section-description">
              소스 설정과 수동 수집은 해당 과제 API 연결 후 활성화됩니다.
            </p>
          </div>
          <button className="mode-button" disabled type="button">
            수동 실행
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[42rem] text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-5 py-3 font-semibold">기관</th>
                <th className="px-5 py-3 font-semibold">게시판</th>
                <th className="px-5 py-3 font-semibold">수집 상태</th>
                <th className="px-5 py-3 font-semibold">최종 실행</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-100">
                <td className="px-5 py-10 text-center text-slate-400" colSpan={4}>
                  연결된 모니터링 소스가 없습니다.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

export default PublicMonitorPage
