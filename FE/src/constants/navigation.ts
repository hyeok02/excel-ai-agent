export const ROUTES = {
  dashboard: '/',
  publicMonitor: '/public-monitor',
  personNews: '/person-news',
  newsCollection: '/news-collection',
  excelAnalysis: '/excel-analysis',
  login: '/login',
  authCallback: '/auth/callback',
  userManagement: '/admin/users',
} as const

export const DASHBOARD_NAVIGATION_ITEM = {
  to: ROUTES.dashboard,
  label: '대시보드',
  description: '공통 운영 현황',
} as const

export const BUSINESS_NAVIGATION_ITEMS = [
  {
    id: 'public-monitor',
    to: ROUTES.publicMonitor,
    label: '공공기관 모니터',
    description: '기관 게시판 모니터링',
  },
  {
    id: 'person-news',
    to: ROUTES.personNews,
    label: '인물 뉴스 추적',
    description: '인물별 뉴스 인사이트',
  },
  {
    id: 'news-collection',
    to: ROUTES.newsCollection,
    label: '뉴스 수집',
    description: '키워드 기반 뉴스 수집',
  },
  {
    id: 'excel-analysis',
    to: ROUTES.excelAnalysis,
    label: 'Excel 분석',
    description: '워크북 구조 분석',
  },
] as const
