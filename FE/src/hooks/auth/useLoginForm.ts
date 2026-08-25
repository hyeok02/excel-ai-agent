import axios from 'axios'
import { type FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getSsoLoginUrl } from '@/api/auth'
import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'
import { getErrorMessage } from '@/utils/apiClient'

export type LoginMode = 'LOCAL' | 'SSO'

interface LoginLocationState {
  from?: string
}

const useLoginForm = () => {
  const { config, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<LoginMode>('LOCAL')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      if (mode === 'SSO') {
        if (!config?.ssoEnabled) {
          setError('회사 SSO가 아직 설정되지 않았습니다.')
          return
        }
        window.location.assign(getSsoLoginUrl(config.ssoLoginPath))
        return
      }

      await login(username, password)
      const destination = (location.state as LoginLocationState | null)?.from
      navigate(destination ?? ROUTES.dashboard, { replace: true })
    } catch (loginError) {
      if (axios.isAxiosError(loginError) && loginError.response?.status === 404) {
        setError(
          '로그인 API를 찾을 수 없습니다. 백엔드 서버를 최신 코드로 다시 실행해주세요.',
        )
      } else {
        setError(getErrorMessage(loginError))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    config,
    error,
    handleSubmit,
    isSubmitting,
    mode,
    password,
    setMode,
    setPassword,
    setUsername,
    username,
  }
}

export default useLoginForm
