import { type ReactNode, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import AdminRoute from '@/components/auth/guards/AdminRoute'
import ProtectedRoute from '@/components/auth/guards/ProtectedRoute'
import { ROUTES } from '@/constants/navigation'
import RootLayout from '@/layouts/RootLayout'
import {
  AnalysisPage,
  AuthCallbackPage,
  DashboardPage,
  LoginPage,
  NewsCollectionPage,
  NotFoundPage,
  PersonNewsPage,
  PublicMonitorPage,
  UserManagementPage,
} from '@/routes/LazyPages'

const page = (content: ReactNode) => (
  <Suspense
    fallback={
      <p className="p-6 text-sm font-semibold text-slate-500">화면 불러오는 중…</p>
    }
  >
    {content}
  </Suspense>
)

const router = createBrowserRouter([
  {
    path: ROUTES.dashboard,
    element: (
      <ProtectedRoute>
        <RootLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: page(<DashboardPage />) },
      { path: ROUTES.publicMonitor.slice(1), element: page(<PublicMonitorPage />) },
      { path: ROUTES.personNews.slice(1), element: page(<PersonNewsPage />) },
      { path: ROUTES.newsCollection.slice(1), element: page(<NewsCollectionPage />) },
      { path: ROUTES.excelAnalysis.slice(1), element: page(<AnalysisPage />) },
      {
        path: ROUTES.userManagement.slice(1),
        element: <AdminRoute>{page(<UserManagementPage />)}</AdminRoute>,
      },
      { path: '*', element: page(<NotFoundPage />) },
    ],
  },
  { path: ROUTES.login, element: page(<LoginPage />) },
  { path: ROUTES.authCallback, element: page(<AuthCallbackPage />) },
])

export default router
