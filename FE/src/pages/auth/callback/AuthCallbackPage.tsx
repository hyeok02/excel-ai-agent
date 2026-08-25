import { LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'

const AuthCallbackPage = () => {
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [message, setMessage] = useState('회사 계정 인증을 확인하고 있습니다.')

  useEffect(() => {
    const complete = async () => {
      if (searchParams.has('error')) {
        navigate(ROUTES.login, { replace: true, state: { ssoError: true } })
        return
      }
      const user = await refresh()
      if (user) {
        navigate(ROUTES.dashboard, { replace: true })
      } else {
        setMessage('인증 정보를 확인할 수 없습니다. 다시 로그인해주세요.')
        window.setTimeout(() => navigate(ROUTES.login, { replace: true }), 1500)
      }
    }
    void complete()
  }, [navigate, refresh, searchParams])

  return (
    <main className="grid min-h-dvh place-items-center bg-app-background p-6">
      <div className="panel flex max-w-sm flex-col items-center p-9 text-center">
        <LoaderCircle className="animate-spin text-brand-600" size={30} />
        <p className="mt-5 text-sm font-bold text-slate-800">{message}</p>
      </div>
    </main>
  )
}

export default AuthCallbackPage
