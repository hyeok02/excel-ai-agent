import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import LoginCard from '@/components/auth/login/LoginCard'
import LoginHeroPanel from '@/components/auth/login/LoginHeroPanel'
import { ROUTES } from '@/constants/navigation'
import useLoginForm from '@/hooks/auth/useLoginForm'

const LoginPage = () => {
  const { user } = useAuth()
  const loginForm = useLoginForm()

  useEffect(() => {
    document.documentElement.classList.add('auth-screen')
    return () => document.documentElement.classList.remove('auth-screen')
  }, [])

  if (user) return <Navigate replace to={ROUTES.dashboard} />

  return (
    <main className="relative isolate min-h-dvh w-full overflow-hidden bg-gradient-to-br from-[#0b3f9d] via-[#1769e0] to-[#5ea3ff] px-4 py-5 sm:px-6 lg:p-0">
      <div className="pointer-events-none absolute -right-24 -top-32 size-[32rem] rounded-full border border-white/10 bg-white/[0.025]" />
      <div className="pointer-events-none absolute -bottom-56 right-[15%] size-[36rem] rounded-full border border-white/10 bg-white/[0.035]" />
      <div className="pointer-events-none absolute left-[36%] top-[-14rem] size-[30rem] rounded-full border border-white/[0.08]" />

      <div className="relative mx-auto min-h-[calc(100dvh-2.5rem)] w-full max-w-[105rem] lg:grid lg:min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <LoginHeroPanel />
        <LoginCard
          config={loginForm.config}
          error={loginForm.error}
          isSubmitting={loginForm.isSubmitting}
          mode={loginForm.mode}
          onModeChange={loginForm.setMode}
          onPasswordChange={loginForm.setPassword}
          onSubmit={loginForm.handleSubmit}
          onUsernameChange={loginForm.setUsername}
          password={loginForm.password}
          username={loginForm.username}
        />
      </div>
    </main>
  )
}

export default LoginPage
