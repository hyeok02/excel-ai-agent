import { type PropsWithChildren } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'

const AdminRoute = ({ children }: PropsWithChildren) => {
  const { user } = useAuth()
  return user?.role === 'ADMIN' ? children : <Navigate replace to={ROUTES.dashboard} />
}

export default AdminRoute
