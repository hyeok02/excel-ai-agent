import { lazy } from 'react'

export const UserManagementPage = lazy(
  () => import('@/pages/admin/users/UserManagementPage'),
)
export const AnalysisPage = lazy(() => import('@/pages/analysis/AnalysisPage'))
export const AuthCallbackPage = lazy(
  () => import('@/pages/auth/callback/AuthCallbackPage'),
)
export const LoginPage = lazy(() => import('@/pages/auth/login/LoginPage'))
export const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))
export const NewsCollectionPage = lazy(
  () => import('@/pages/news-collection/NewsCollectionPage'),
)
export const NotFoundPage = lazy(() => import('@/pages/not-found/NotFoundPage'))
export const PersonNewsPage = lazy(() => import('@/pages/person-news/PersonNewsPage'))
export const PublicMonitorPage = lazy(
  () => import('@/pages/public-monitor/PublicMonitorPage'),
)
