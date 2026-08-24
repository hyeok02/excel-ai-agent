import axios from 'axios'
import {
  Building2,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { getSsoLoginUrl } from '@/api/auth'
import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'
import { getErrorMessage } from '@/utils/apiClient'
import { cn } from '@/utils/cn'

type LoginMode = 'LOCAL' | 'SSO'

interface LoginLocationState {
  from?: string
}

const LoginPage = () => {
  const { user, config, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<LoginMode>('LOCAL')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    document.documentElement.classList.add('auth-screen')
    return () => document.documentElement.classList.remove('auth-screen')
  }, [])

  if (user) {
    return <Navigate replace to={ROUTES.dashboard} />
  }

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

  return (
    <main className="relative isolate min-h-dvh w-full overflow-hidden bg-gradient-to-br from-[#0b3f9d] via-[#1769e0] to-[#5ea3ff] px-4 py-5 sm:px-6 lg:p-0">
      <div className="pointer-events-none absolute -right-24 -top-32 size-[32rem] rounded-full border border-white/10 bg-white/[0.025]" />
      <div className="pointer-events-none absolute -bottom-56 right-[15%] size-[36rem] rounded-full border border-white/10 bg-white/[0.035]" />
      <div className="pointer-events-none absolute left-[36%] top-[-14rem] size-[30rem] rounded-full border border-white/[0.08]" />

      <div className="relative mx-auto min-h-[calc(100dvh-2.5rem)] w-full max-w-[105rem] lg:grid lg:min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <section className="relative hidden min-w-0 px-[clamp(4rem,7vw,8rem)] py-14 text-white lg:flex lg:flex-col lg:justify-between xl:py-16">
          <div className="auth-reveal auth-reveal-delay-1 flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-[0.9rem] border border-white/15 bg-white/10 text-blue-100 shadow-lg backdrop-blur">
              <Sparkles size={20} strokeWidth={2.1} />
            </span>
            <div>
              <p className="text-[1.05rem] font-extrabold tracking-[-0.025em]">
                Decision Support
              </p>
              <p className="mt-1 text-[0.7rem] font-bold tracking-[0.18em] text-blue-200/75">
                AI WORKSPACE
              </p>
            </div>
          </div>

          <div className="auth-reveal auth-reveal-delay-2 max-w-[38rem] pb-6 xl:pb-10">
            <div className="flex items-center gap-3 text-[0.72rem] font-bold tracking-[0.16em] text-blue-200">
              <span className="h-px w-8 bg-blue-300/70" />
              DECISION INTELLIGENCE
            </div>
            <h1 className="mt-7 text-[2.75rem] font-extrabold leading-[1.14] tracking-[-0.05em] xl:text-[3.15rem] 2xl:text-[3.45rem]">
              복잡한 데이터에서
              <br />
              명확한 판단까지.
            </h1>
            <p className="mt-6 max-w-[35rem] text-[1.1rem] leading-8 text-blue-50/85">
              <span className="block">사내 데이터와 AI Agent를 안전하게 연결하고,</span>
              <span className="block">
                복잡한 Excel 구조를 근거 있는 인사이트로 전환합니다.
              </span>
            </p>

            <div className="mt-9 flex flex-wrap gap-2.5">
              {['근거 기반 분석', '역할 기반 보안', '통합 업무 기록'].map((item) => (
                <span
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.055] px-3.5 py-2 text-[0.78rem] font-semibold text-blue-50 backdrop-blur"
                  key={item}
                >
                  <span className="size-1.5 rounded-full bg-blue-300" />
                  {item}
                </span>
              ))}
            </div>
          </div>

          <p className="auth-reveal auth-reveal-delay-3 text-[1.1rem] font-normal leading-8 tracking-[-0.015em] text-blue-100/45">
            Secure internal access · Decision Support System
          </p>
        </section>

        <section className="relative flex min-h-[calc(100dvh-2.5rem)] min-w-0 items-center justify-center lg:min-h-dvh lg:border-l lg:border-white/[0.08] lg:bg-white/[0.025] lg:px-10 xl:px-16">
          <div className="auth-card-reveal w-full max-w-[29rem] rounded-[2.25rem] border border-white/60 bg-white/[0.96] p-6 shadow-[0_36px_100px_rgb(4_30_85/34%)] backdrop-blur-xl sm:p-9 xl:p-10">
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <span className="grid size-10 place-items-center rounded-2xl bg-brand-600 text-white shadow-brand">
                <Sparkles size={19} />
              </span>
              <div>
                <p className="font-extrabold tracking-[-0.03em] text-slate-950">
                  Decision Support
                </p>
                <p className="text-[0.72rem] font-bold tracking-[0.12em] text-slate-400">
                  AI WORKSPACE
                </p>
              </div>
            </div>

            <div>
              <p className="eyebrow !text-[0.78rem]">WELCOME BACK</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.045em] text-slate-950">
                업무 공간에 로그인
              </h2>
              <p className="mt-2 text-[0.9rem] leading-6 text-slate-500">
                관리자가 발급한 사내 계정 또는 회사 SSO를 사용하세요.
              </p>
            </div>

            {config?.ssoEnabled && (
              <div
                className="mt-7 grid grid-cols-2 rounded-xl bg-slate-100 p-1"
                role="tablist"
              >
                <button
                  className={cn(
                    'auth-mode-tab !text-[0.8rem]',
                    mode === 'LOCAL' && 'auth-mode-tab-active',
                  )}
                  onClick={() => setMode('LOCAL')}
                  role="tab"
                  type="button"
                >
                  사내 계정
                </button>
                <button
                  className={cn(
                    'auth-mode-tab !text-[0.8rem]',
                    mode === 'SSO' && 'auth-mode-tab-active',
                  )}
                  onClick={() => setMode('SSO')}
                  role="tab"
                  type="button"
                >
                  회사 SSO
                </button>
              </div>
            )}

            <form className="mt-7" onSubmit={handleSubmit}>
              {mode === 'LOCAL' ? (
                <div className="space-y-5">
                  <label className="block">
                    <span className="auth-field-label !text-[0.8rem]">아이디</span>
                    <span className="auth-input-wrap">
                      <KeyRound aria-hidden="true" size={18} />
                      <input
                        autoComplete="username"
                        autoFocus
                        className="!text-[0.95rem]"
                        onChange={(event) => setUsername(event.target.value)}
                        placeholder="사내 계정 아이디"
                        required
                        value={username}
                      />
                    </span>
                  </label>
                  <label className="block">
                    <span className="auth-field-label !text-[0.8rem]">비밀번호</span>
                    <span className="auth-input-wrap">
                      <LockKeyhole aria-hidden="true" size={18} />
                      <input
                        autoComplete="current-password"
                        className="!text-[0.95rem]"
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="비밀번호 입력"
                        required
                        type="password"
                        value={password}
                      />
                    </span>
                  </label>
                </div>
              ) : (
                <div className="rounded-2xl border border-brand-100 bg-brand-50/60 p-6 text-center">
                  <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-brand-600 shadow-sm">
                    <Building2 size={22} />
                  </span>
                  <p className="mt-4 text-[0.9rem] font-bold text-slate-900">
                    회사 통합 인증
                  </p>
                  <p className="mt-1 text-[0.78rem] leading-5 text-slate-500">
                    회사 인증 페이지에서 계정을 확인한 후 자동으로 돌아옵니다.
                  </p>
                </div>
              )}

              {error && (
                <div
                  className="mt-5 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-600"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                className="button-primary mt-7 flex h-12 w-full gap-2 !text-[0.92rem]"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? (
                  <LoaderCircle className="animate-spin" size={18} />
                ) : (
                  <ShieldCheck size={18} />
                )}
                로그인
              </button>
            </form>

            <div className="mt-6 flex items-start gap-2.5 border-t border-slate-100 pt-5 text-[0.78rem] leading-5 text-slate-500/80">
              <LockKeyhole className="mt-0.5 shrink-0" size={14} />본 시스템은 승인된
              임직원만 사용할 수 있으며 접속 및 주요 활동이 보안 정책에 따라 관리됩니다.
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

export default LoginPage
