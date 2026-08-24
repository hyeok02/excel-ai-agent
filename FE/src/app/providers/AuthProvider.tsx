import { type PropsWithChildren, useCallback, useEffect, useMemo, useState } from 'react'

import {
  type AuthConfig,
  type CurrentUser,
  getAuthConfig,
  getCurrentUser,
  initializeCsrf,
  loginWithCredentials,
  logout as requestLogout,
} from '@/api/auth'
import { AuthContext, type AuthContextValue } from '@/app/providers/auth-context'

const AuthProvider = ({ children }: PropsWithChildren) => {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [config, setConfig] = useState<AuthConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser)
      return currentUser
    } catch {
      setUser(null)
      return null
    }
  }, [])

  useEffect(() => {
    const initialize = async () => {
      try {
        const [authConfig] = await Promise.all([getAuthConfig(), initializeCsrf()])
        setConfig(authConfig)
        await refresh()
      } finally {
        setIsLoading(false)
      }
    }

    void initialize()
  }, [refresh])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      config,
      isLoading,
      login: async (username, password) => {
        await initializeCsrf()
        const authenticatedUser = await loginWithCredentials(username, password)
        setUser(authenticatedUser)
        return authenticatedUser
      },
      logout: async () => {
        await requestLogout()
        setUser(null)
        await initializeCsrf()
      },
      refresh,
    }),
    [config, isLoading, refresh, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export default AuthProvider
