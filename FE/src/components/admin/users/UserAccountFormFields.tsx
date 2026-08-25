import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface AccountTextFieldProps {
  icon: LucideIcon
  label: string
  maxLength?: number
  minLength?: number
  onChange: (value: string) => void
  pattern?: string
  placeholder: string
  type?: 'text' | 'password'
  value: string
}

export const AccountTextField = ({
  icon: Icon,
  label,
  onChange,
  ...inputProps
}: AccountTextFieldProps) => (
  <label className="block">
    <span className="auth-field-label">{label}</span>
    <span className="auth-input-wrap">
      <Icon size={17} />
      <input
        {...inputProps}
        onChange={(event) => onChange(event.target.value)}
        required
      />
    </span>
  </label>
)

export const FormMessage = ({
  children,
  tone,
}: {
  children: ReactNode
  tone: 'error' | 'success'
}) => (
  <p
    className={
      tone === 'error'
        ? 'rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-600'
        : 'flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700'
    }
  >
    {children}
  </p>
)
