import { createContext, useContext } from 'react'

import { type AuthConfig, type CurrentUser } from '@/api/auth'

export interface AuthContextValue {
  user: CurrentUser | null
  config: AuthConfig | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<CurrentUser>
  logout: () => Promise<void>
  refresh: () => Promise<CurrentUser | null>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth는 AuthProvider 내부에서 사용해야 합니다.')
  }
  return context
}
