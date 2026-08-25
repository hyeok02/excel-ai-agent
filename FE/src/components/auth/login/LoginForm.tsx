import { KeyRound, LoaderCircle, LockKeyhole, ShieldCheck } from 'lucide-react'
import type { Dispatch, FormEvent, SetStateAction } from 'react'

import {
  LoginField,
  LoginModeTabs,
  SsoDescription,
} from '@/components/auth/login/LoginFormFields'
import type { LoginMode } from '@/hooks/auth/useLoginForm'

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

export default LoginForm
