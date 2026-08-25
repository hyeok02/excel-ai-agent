import {
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  Plus,
  UserRound,
  UsersRound,
} from 'lucide-react'
import type { Dispatch, FormEvent, SetStateAction } from 'react'

import type { CreateUserRequest } from '@/api/auth'

interface UserAccountFormProps {
  error: string | null
  form: CreateUserRequest
  isSubmitting: boolean
  onFormChange: Dispatch<SetStateAction<CreateUserRequest>>
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  success: string | null
}

const UserAccountForm = ({
  error,
  form,
  isSubmitting,
  onFormChange,
  onSubmit,
  success,
}: UserAccountFormProps) => (
  <section className="panel p-6">
    <div className="flex items-center gap-3">
      <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
        <Plus size={19} />
      </span>
      <div>
        <h2 className="section-title">사내 계정 발급</h2>
        <p className="section-description">사용자에게 전달할 로그인 정보를 생성합니다.</p>
      </div>
    </div>

    <form className="mt-6 space-y-4" onSubmit={onSubmit}>
      <AccountTextField
        icon={UserRound}
        label="이름"
        maxLength={100}
        onChange={(displayName) =>
          onFormChange((current) => ({ ...current, displayName }))
        }
        placeholder="홍길동"
        value={form.displayName}
      />
      <AccountTextField
        icon={UsersRound}
        label="아이디"
        minLength={3}
        onChange={(username) => onFormChange((current) => ({ ...current, username }))}
        pattern="[A-Za-z0-9._-]+"
        placeholder="employee01"
        value={form.username}
      />
      <AccountTextField
        icon={KeyRound}
        label="임시 비밀번호"
        minLength={8}
        onChange={(password) => onFormChange((current) => ({ ...current, password }))}
        placeholder="8자 이상 입력"
        type="password"
        value={form.password}
      />
      <label className="block">
        <span className="auth-field-label">권한</span>
        <select
          className="auth-select"
          onChange={(event) =>
            onFormChange((current) => ({
              ...current,
              role: event.target.value as CreateUserRequest['role'],
            }))
          }
          value={form.role}
        >
          <option value="USER">일반 사용자</option>
          <option value="ADMIN">관리자</option>
        </select>
      </label>

      {error && <FormMessage tone="error">{error}</FormMessage>}
      {success && (
        <FormMessage tone="success">
          <CheckCircle2 size={16} /> {success}
        </FormMessage>
      )}

      <button
        className="button-primary flex h-11 w-full gap-2"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? (
          <LoaderCircle className="animate-spin" size={17} />
        ) : (
          <Plus size={17} />
        )}
        계정 생성
      </button>
    </form>
  </section>
)

interface AccountTextFieldProps {
  icon: typeof UserRound
  label: string
  maxLength?: number
  minLength?: number
  onChange: (value: string) => void
  pattern?: string
  placeholder: string
  type?: 'text' | 'password'
  value: string
}

const AccountTextField = ({
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

const FormMessage = ({
  children,
  tone,
}: {
  children: React.ReactNode
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

export default UserAccountForm
