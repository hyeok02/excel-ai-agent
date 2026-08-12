import { Building2, FileSpreadsheet, Newspaper, UserRoundSearch } from 'lucide-react'
import { Link } from 'react-router-dom'

import { BUSINESS_NAVIGATION_ITEMS } from '@/constants/navigation'

const MODULE_SUMMARIES = [
  {
    id: 'public-monitor',
    title: '공공기관 모니터',
    summary: '게시판 변화를 놓치지 않도록 자동으로 확인합니다.',
    tone: 'blue',
    icon: Building2,
  },
  {
    id: 'person-news',
    title: '인물 뉴스 추적',
    summary: '주요 인물의 최신 이슈와 맥락을 한눈에 봅니다.',
    tone: 'violet',
    icon: UserRoundSearch,
  },
  {
    id: 'news-collection',
    title: '뉴스 수집',
    summary: '관심 키워드의 뉴스를 수집하고 분류합니다.',
    tone: 'amber',
    icon: Newspaper,
  },
  {
    id: 'excel-analysis',
    title: 'Excel 분석',
    summary: '복잡한 워크북 구조를 읽고 인사이트를 찾습니다.',
    tone: 'emerald',
    icon: FileSpreadsheet,
  },
]

const DashboardPage = () => {
  return (
    <div className="space-y-8">
      <section className="dashboard-hero">
        <div className="relative z-10 max-w-3xl">
          <span className="hero-badge">AI DECISION WORKSPACE</span>
          <h1 className="mt-5 text-3xl font-extrabold leading-tight tracking-[-0.045em] text-white md:text-[2.7rem]">
            복잡한 데이터를,
            <br />더 빠른 판단으로 바꿉니다.
          </h1>
          <p className="mt-5 max-w-xl text-sm leading-6 text-blue-100 md:text-base">
            외부 데이터 수집부터 Excel 구조 분석까지, 네 가지 AI 업무를 하나의 공간에서
            관리하세요.
          </p>
        </div>
        <div className="hero-orbit hero-orbit-one" />
        <div className="hero-orbit hero-orbit-two" />
      </section>

      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">WORKSPACE</p>
            <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
              업무 바로가기
            </h2>
          </div>
          <p className="hidden text-sm text-slate-400 sm:block">4개의 AI 업무 모듈</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {MODULE_SUMMARIES.map((module, index) => {
            const navigationItem = BUSINESS_NAVIGATION_ITEMS.find(
              (item) => item.id === module.id,
            )
            const Icon = module.icon
            const content = (
              <>
                <div className="flex items-center justify-between">
                  <span className={`module-icon module-icon-${module.tone}`}>
                    <Icon aria-hidden="true" size={20} strokeWidth={1.9} />
                  </span>
                  <span className="text-xs font-bold text-slate-300">0{index + 1}</span>
                </div>
                <h3 className="mt-8 text-lg font-extrabold tracking-tight text-slate-950">
                  {module.title}
                </h3>
                <p className="mt-2 min-h-10 text-sm leading-5 text-slate-500">
                  {module.summary}
                </p>
                <span className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-brand-600">
                  열어보기 <span aria-hidden="true">→</span>
                </span>
              </>
            )

            return navigationItem ? (
              <Link className="module-card" key={module.id} to={navigationItem.to}>
                {content}
              </Link>
            ) : null
          })}
        </div>
      </section>
    </div>
  )
}

export default DashboardPage
