import { Building2, KeyRound, LoaderCircle, LockKeyhole, ShieldCheck } from 'lucide-react'
import type { Dispatch, FormEvent, SetStateAction } from 'react'

import type { LoginMode } from '@/hooks/auth/useLoginForm'
import { cn } from '@/utils/cn'

export interface LoginFormProps {
  error: string | null
  isSubmitting: boolean
  mode: LoginMode
  onModeChange: Dispatch<SetStateAction<LoginMode>>
  onPasswordChange: Dispatch<SetStateAction<string>>
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onUsernameChange: Dispatch<SetStateAction<string>>
  password: string
  ssoEnabled: boolean
  username: string
}

const LoginForm = ({
  error,
  isSubmitting,
  mode,
  onModeChange,
  onPasswordChange,
  onSubmit,
  onUsernameChange,
  password,
  ssoEnabled,
  username,
}: LoginFormProps) => (
  <>
    {ssoEnabled && <LoginModeTabs mode={mode} onModeChange={onModeChange} />}

    <form className="mt-7" onSubmit={onSubmit}>
      {mode === 'LOCAL' ? (
        <div className="space-y-5">
          <LoginField
            autoComplete="username"
            autoFocus
            icon={KeyRound}
            label="아이디"
            onChange={onUsernameChange}
            placeholder="사내 계정 아이디"
            value={username}
          />
          <LoginField
            autoComplete="current-password"
            icon={LockKeyhole}
            label="비밀번호"
            onChange={onPasswordChange}
            placeholder="비밀번호 입력"
            type="password"
            value={password}
          />
        </div>
      ) : (
        <SsoDescription />
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
  </>
)

const LoginModeTabs = ({
  mode,
  onModeChange,
}: {
  mode: LoginMode
  onModeChange: Dispatch<SetStateAction<LoginMode>>
}) => (
  <div className="mt-7 grid grid-cols-2 rounded-xl bg-slate-100 p-1" role="tablist">
    {(
      [
        ['LOCAL', '사내 계정'],
        ['SSO', '회사 SSO'],
      ] as const
    ).map(([value, label]) => (
      <button
        className={cn(
          'auth-mode-tab !text-[0.8rem]',
          mode === value && 'auth-mode-tab-active',
        )}
        key={value}
        onClick={() => onModeChange(value)}
        role="tab"
        type="button"
      >
        {label}
      </button>
    ))}
  </div>
)

interface LoginFieldProps {
  autoComplete: string
  autoFocus?: boolean
  icon: typeof KeyRound
  label: string
  onChange: Dispatch<SetStateAction<string>>
  placeholder: string
  type?: 'text' | 'password'
  value: string
}

const LoginField = ({ icon: Icon, label, onChange, ...inputProps }: LoginFieldProps) => (
  <label className="block">
    <span className="auth-field-label !text-[0.8rem]">{label}</span>
    <span className="auth-input-wrap">
      <Icon aria-hidden="true" size={18} />
      <input
        {...inputProps}
        className="!text-[0.95rem]"
        onChange={(event) => onChange(event.target.value)}
        required
      />
    </span>
  </label>
)

const SsoDescription = () => (
  <div className="rounded-2xl border border-brand-100 bg-brand-50/60 p-6 text-center">
    <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-white text-brand-600 shadow-sm">
      <Building2 size={22} />
    </span>
    <p className="mt-4 text-[0.9rem] font-bold text-slate-900">회사 통합 인증</p>
    <p className="mt-1 text-[0.78rem] leading-5 text-slate-500">
      회사 인증 페이지에서 계정을 확인한 후 자동으로 돌아옵니다.
    </p>
  </div>
)

export default LoginForm
