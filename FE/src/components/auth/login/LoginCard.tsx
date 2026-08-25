import { LockKeyhole, Sparkles } from 'lucide-react'

import type { AuthConfig } from '@/api/auth'
import LoginForm, { type LoginFormProps } from '@/components/auth/login/LoginForm'

interface LoginCardProps extends Omit<LoginFormProps, 'ssoEnabled'> {
  config: AuthConfig | null
}

const LoginCard = ({ config, ...formProps }: LoginCardProps) => (
  <section className="relative flex min-h-[calc(100dvh-2.5rem)] min-w-0 items-center justify-center lg:min-h-dvh lg:border-l lg:border-white/[0.08] lg:bg-white/[0.025] lg:px-10 xl:px-16">
    <div className="auth-card-reveal w-full max-w-[29rem] rounded-[2.25rem] border border-white/60 bg-white/[0.96] p-6 shadow-[0_36px_100px_rgb(4_30_85/34%)] backdrop-blur-xl sm:p-9 xl:p-10">
      <MobileBrand />
      <div>
        <p className="eyebrow !text-[0.78rem]">WELCOME BACK</p>
        <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.045em] text-slate-950">
          업무 공간에 로그인
        </h2>
        <p className="mt-2 text-[0.9rem] leading-6 text-slate-500">
          관리자가 발급한 사내 계정 또는 회사 SSO를 사용하세요.
        </p>
      </div>

      <LoginForm {...formProps} ssoEnabled={config?.ssoEnabled ?? false} />

      <div className="mt-6 flex items-start gap-2.5 border-t border-slate-100 pt-5 text-[0.78rem] leading-5 text-slate-500/80">
        <LockKeyhole className="mt-0.5 shrink-0" size={14} />본 시스템은 승인된 임직원만
        사용할 수 있으며 접속 및 주요 활동이 보안 정책에 따라 관리됩니다.
      </div>
    </div>
  </section>
)

const MobileBrand = () => (
  <div className="mb-8 flex items-center gap-3 lg:hidden">
    <span className="grid size-10 place-items-center rounded-2xl bg-brand-600 text-white shadow-brand">
      <Sparkles size={19} />
    </span>
    <div>
      <p className="font-extrabold tracking-[-0.03em] text-slate-950">Decision Support</p>
      <p className="text-[0.72rem] font-bold tracking-[0.12em] text-slate-400">
        AI WORKSPACE
      </p>
    </div>
  </div>
)

export default LoginCard
