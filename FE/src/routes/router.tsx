import { createBrowserRouter } from 'react-router-dom'

import AdminRoute from '@/components/auth/AdminRoute'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { ROUTES } from '@/constants/navigation'
import RootLayout from '@/layouts/RootLayout'
import UserManagementPage from '@/pages/admin/UserManagementPage'
import AnalysisPage from '@/pages/analysis/AnalysisPage'
import AuthCallbackPage from '@/pages/auth/AuthCallbackPage'
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import NewsCollectionPage from '@/pages/news-collection/NewsCollectionPage'
import NotFoundPage from '@/pages/not-found/NotFoundPage'
import PersonNewsPage from '@/pages/person-news/PersonNewsPage'
import PublicMonitorPage from '@/pages/public-monitor/PublicMonitorPage'

const router = createBrowserRouter([
  {
    path: ROUTES.dashboard,
    element: (
      <ProtectedRoute>
        <RootLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: ROUTES.publicMonitor.slice(1), element: <PublicMonitorPage /> },
      { path: ROUTES.personNews.slice(1), element: <PersonNewsPage /> },
      { path: ROUTES.newsCollection.slice(1), element: <NewsCollectionPage /> },
      { path: ROUTES.excelAnalysis.slice(1), element: <AnalysisPage /> },
      {
        path: ROUTES.userManagement.slice(1),
        element: (
          <AdminRoute>
            <UserManagementPage />
          </AdminRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  { path: ROUTES.login, element: <LoginPage /> },
  { path: ROUTES.authCallback, element: <AuthCallbackPage /> },
])

export default router
