import {
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  Plus,
  ShieldCheck,
  UserRound,
  UsersRound,
} from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'

import {
  createUser,
  type CreateUserRequest,
  listUsers,
  type ManagedUser,
} from '@/api/auth'
import { getErrorMessage } from '@/utils/apiClient'

const INITIAL_FORM: CreateUserRequest = {
  username: '',
  password: '',
  displayName: '',
  role: 'USER',
}

const UserManagementPage = () => {
  const [users, setUsers] = useState<ManagedUser[]>([])
  const [form, setForm] = useState<CreateUserRequest>(INITIAL_FORM)
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        setUsers(await listUsers())
      } catch (loadError) {
        setError(getErrorMessage(loadError))
      } finally {
        setIsLoading(false)
      }
    }
    void load()
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSuccess(null)
    setIsSubmitting(true)
    try {
      const created = await createUser(form)
      setUsers((current) => [created, ...current])
      setForm(INITIAL_FORM)
      setSuccess(`${created.displayName} 계정을 생성했습니다.`)
    } catch (createError) {
      setError(getErrorMessage(createError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-7">
      <div className="page-heading">
        <div>
          <p className="eyebrow">ACCESS MANAGEMENT</p>
          <h1 className="page-title">사용자 관리</h1>
          <p className="page-description">
            사내 계정을 발급하고 시스템 접근 권한을 관리합니다.
          </p>
        </div>
        <div className="status-pill" data-status="success">
          <span /> 사용자 {users.length}명
        </div>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[24rem_1fr]">
        <section className="panel p-6">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-600">
              <Plus size={19} />
            </span>
            <div>
              <h2 className="section-title">사내 계정 발급</h2>
              <p className="section-description">
                사용자에게 전달할 로그인 정보를 생성합니다.
              </p>
            </div>
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="auth-field-label">이름</span>
              <span className="auth-input-wrap">
                <UserRound size={17} />
                <input
                  maxLength={100}
                  onChange={(event) =>
                    setForm({ ...form, displayName: event.target.value })
                  }
                  placeholder="홍길동"
                  required
                  value={form.displayName}
                />
              </span>
            </label>
            <label className="block">
              <span className="auth-field-label">아이디</span>
              <span className="auth-input-wrap">
                <UsersRound size={17} />
                <input
                  minLength={3}
                  onChange={(event) => setForm({ ...form, username: event.target.value })}
                  pattern="[A-Za-z0-9._-]+"
                  placeholder="employee01"
                  required
                  value={form.username}
                />
              </span>
            </label>
            <label className="block">
              <span className="auth-field-label">임시 비밀번호</span>
              <span className="auth-input-wrap">
                <KeyRound size={17} />
                <input
                  minLength={8}
                  onChange={(event) => setForm({ ...form, password: event.target.value })}
                  placeholder="8자 이상 입력"
                  required
                  type="password"
                  value={form.password}
                />
              </span>
            </label>
            <label className="block">
              <span className="auth-field-label">권한</span>
              <select
                className="auth-select"
                onChange={(event) =>
                  setForm({
                    ...form,
                    role: event.target.value as CreateUserRequest['role'],
                  })
                }
                value={form.role}
              >
                <option value="USER">일반 사용자</option>
                <option value="ADMIN">관리자</option>
              </select>
            </label>

            {error && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-600">
                {error}
              </p>
            )}
            {success && (
              <p className="flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                <CheckCircle2 size={16} /> {success}
              </p>
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

        <section className="panel overflow-hidden">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="section-title">등록 사용자</h2>
            <p className="section-description">
              로컬 계정과 SSO 사용자를 함께 확인합니다.
            </p>
          </div>

          {isLoading ? (
            <div className="flex min-h-64 items-center justify-center gap-2 text-sm text-slate-500">
              <LoaderCircle className="animate-spin" size={18} /> 사용자 목록을 불러오는
              중
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[42rem] text-left">
                <thead className="bg-slate-50/80 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-slate-400">
                  <tr>
                    <th className="px-6 py-3.5">사용자</th>
                    <th className="px-5 py-3.5">로그인 방식</th>
                    <th className="px-5 py-3.5">권한</th>
                    <th className="px-5 py-3.5">상태</th>
                    <th className="px-6 py-3.5">등록일</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((user) => (
                    <tr className="text-sm text-slate-600" key={user.id}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-xs font-extrabold text-brand-700">
                            {user.displayName.slice(0, 1).toUpperCase()}
                          </span>
                          <div>
                            <p className="font-bold text-slate-900">{user.displayName}</p>
                            <p className="mt-0.5 text-xs text-slate-400">
                              {user.email ?? user.username}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        {user.authProvider === 'SSO' ? '회사 SSO' : '사내 계정'}
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
                          <ShieldCheck size={13} />{' '}
                          {user.role === 'ADMIN' ? '관리자' : '사용자'}
                        </span>
                      </td>
                      <td className="px-5 py-4">
                        <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600">
                          <span className="size-1.5 rounded-full bg-emerald-500" />{' '}
                          {user.enabled ? '활성' : '비활성'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-400">
                        {new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium' }).format(
                          new Date(user.createdAt),
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default UserManagementPage
