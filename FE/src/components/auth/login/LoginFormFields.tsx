import { Building2, type LucideIcon } from 'lucide-react'
import type { Dispatch, SetStateAction } from 'react'

import type { LoginMode } from '@/hooks/auth/useLoginForm'
import { cn } from '@/utils/cn'

export const LoginModeTabs = ({
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
  icon: LucideIcon
  label: string
  onChange: Dispatch<SetStateAction<string>>
  placeholder: string
  type?: 'text' | 'password'
  value: string
}

export const LoginField = ({
  icon: Icon,
  label,
  onChange,
  ...inputProps
}: LoginFieldProps) => (
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

export const SsoDescription = () => (
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
