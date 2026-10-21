import type { CurrentUser } from '../../api/auth.ts'

export interface AuthSession {
  user: CurrentUser | null
  revision: number
}

export const nextAuthSession = (
  previous: AuthSession,
  user: CurrentUser | null,
  newSession = false,
): AuthSession => ({
  user,
  revision: previous.revision + Number(newSession || previous.user?.id !== user?.id),
})
