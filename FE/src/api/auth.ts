import apiClient, { API_BASE_URL } from '@/utils/apiClient'

export type UserRole = 'ADMIN' | 'USER'
export type AuthProvider = 'LOCAL' | 'SSO'

export interface CurrentUser {
  id: string
  username: string
  displayName: string
  email: string | null
  role: UserRole
  authProvider: AuthProvider
}

export interface AuthConfig {
  ssoEnabled: boolean
  ssoLoginPath: string
}

export interface ManagedUser extends CurrentUser {
  enabled: boolean
  createdAt: string
}

export interface CreateUserRequest {
  username: string
  password: string
  displayName: string
  role: UserRole
}

export const initializeCsrf = async () => {
  await apiClient.get('/api/v1/auth/csrf')
}

export const getAuthConfig = async () => {
  const { data } = await apiClient.get<AuthConfig>('/api/v1/auth/config')
  return data
}

export const getCurrentUser = async () => {
  const { data } = await apiClient.get<CurrentUser>('/api/v1/auth/me')
  return data
}

export const loginWithCredentials = async (username: string, password: string) => {
  const { data } = await apiClient.post<CurrentUser>('/api/v1/auth/login', {
    username,
    password,
  })
  return data
}

export const logout = async () => {
  await apiClient.post('/api/v1/auth/logout')
}

export const getSsoLoginUrl = (path: string) => new URL(path, API_BASE_URL).toString()

export const listUsers = async () => {
  const { data } = await apiClient.get<ManagedUser[]>('/api/v1/admin/users')
  return data
}

export const createUser = async (request: CreateUserRequest) => {
  const { data } = await apiClient.post<ManagedUser>('/api/v1/admin/users', request)
  return data
}
