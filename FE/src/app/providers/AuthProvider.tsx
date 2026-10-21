import {
  Fragment,
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

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
import { initializeAuthSession } from '@/app/providers/authInitialization'
import { type AuthSession, nextAuthSession } from '@/app/providers/authSession'

const AuthProvider = ({ children }: PropsWithChildren) => {
  const [session, setSession] = useState<AuthSession>({ user: null, revision: 0 })
  const user = session.user
  const [config, setConfig] = useState<AuthConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const authRequest = useRef(0)
  const commitUser = useCallback(
    (currentUser: CurrentUser | null, newSession = false) => {
      setSession((previous) => nextAuthSession(previous, currentUser, newSession))
    },
    [],
  )

  const refresh = useCallback(async () => {
    const request = ++authRequest.current
    try {
      const currentUser = await getCurrentUser()
      if (request !== authRequest.current) return null
      commitUser(currentUser)
      return currentUser
    } catch {
      if (request === authRequest.current) commitUser(null)
      return null
    }
  }, [commitUser])

  useEffect(() => {
    let mounted = true
    const request = ++authRequest.current
    void initializeAuthSession({
      config: getAuthConfig,
      csrf: initializeCsrf,
      user: getCurrentUser,
      isMounted: () => mounted,
      isCurrent: () => request === authRequest.current,
      onConfig: setConfig,
      onUser: commitUser,
      onSettled: () => setIsLoading(false),
    })
    return () => {
      mounted = false
    }
  }, [commitUser])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      config,
      isLoading,
      login: async (username, password) => {
        const request = ++authRequest.current
        await initializeCsrf()
        if (request !== authRequest.current)
          throw new DOMException('Login superseded', 'AbortError')
        const authenticatedUser = await loginWithCredentials(username, password)
        if (request !== authRequest.current)
          throw new DOMException('Login superseded', 'AbortError')
        commitUser(authenticatedUser, true)
        setIsLoading(false)
        return authenticatedUser
      },
      logout: async () => {
        const request = ++authRequest.current
        await requestLogout()
        if (request !== authRequest.current) return
        commitUser(null, true)
        await initializeCsrf()
      },
      refresh,
    }),
    [commitUser, config, isLoading, refresh, user],
  )

  return (
    <AuthContext.Provider value={value}>
      <Fragment key={session.revision}>{children}</Fragment>
    </AuthContext.Provider>
  )
}

export default AuthProvider
