import { LoaderCircle } from 'lucide-react'
import { type PropsWithChildren } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'

const ProtectedRoute = ({ children }: PropsWithChildren) => {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="grid min-h-dvh place-items-center bg-app-background">
        <div className="flex items-center gap-3 text-sm font-semibold text-slate-500">
          <LoaderCircle className="animate-spin text-brand-600" size={20} />
          로그인 상태를 확인하고 있습니다.
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to={ROUTES.login} />
  }

  return children
}

export default ProtectedRoute
