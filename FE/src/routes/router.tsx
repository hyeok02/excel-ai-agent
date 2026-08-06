import { createBrowserRouter } from 'react-router-dom'

import { ROUTES } from '@/constants/navigation'
import RootLayout from '@/layouts/RootLayout'
import AnalysisPage from '@/pages/analysis/AnalysisPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import NewsCollectionPage from '@/pages/news-collection/NewsCollectionPage'
import NotFoundPage from '@/pages/not-found/NotFoundPage'
import PersonNewsPage from '@/pages/person-news/PersonNewsPage'
import PublicMonitorPage from '@/pages/public-monitor/PublicMonitorPage'

const router = createBrowserRouter([
  {
    path: ROUTES.dashboard,
    element: <RootLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: ROUTES.publicMonitor.slice(1), element: <PublicMonitorPage /> },
      { path: ROUTES.personNews.slice(1), element: <PersonNewsPage /> },
      { path: ROUTES.newsCollection.slice(1), element: <NewsCollectionPage /> },
      { path: ROUTES.excelAnalysis.slice(1), element: <AnalysisPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default router
