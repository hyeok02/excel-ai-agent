import { Link } from 'react-router-dom'

import { BUSINESS_NAVIGATION_ITEMS } from '@/constants/navigation'

const MODULE_SUMMARIES = [
  { id: 'public-monitor', title: '공공기관 모니터', status: '정적 데모' },
  { id: 'person-news', title: '인물 뉴스 추적', status: '정적 데모' },
  { id: 'news-collection', title: '뉴스 수집', status: '정적 데모' },
  { id: 'excel-analysis', title: 'Excel 분석', status: '구현 대상' },
]

const DashboardPage = () => {
  return (
    <div className="space-y-6">
      <section>
        <p className="eyebrow">DASHBOARD</p>
        <h1 className="page-title">Decision Support System</h1>
        <p className="page-description">
          외부 데이터 기반 AI Agent 업무를 메뉴별로 확인합니다.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {MODULE_SUMMARIES.map((module, index) => {
          const navigationItem = BUSINESS_NAVIGATION_ITEMS.find(
            (item) => item.id === module.id,
          )
          const content = (
            <>
              <span className="text-xs font-bold text-brand-600">0{index + 1}</span>
              <h2 className="mt-8 text-lg font-bold text-slate-950">{module.title}</h2>
              <p className="mt-2 text-sm text-slate-500">{module.status}</p>
            </>
          )

          return navigationItem ? (
            <Link
              className="panel p-5 transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-lg"
              key={module.id}
              to={navigationItem.to}
            >
              {content}
            </Link>
          ) : null
        })}
      </section>
    </div>
  )
}

export default DashboardPage
