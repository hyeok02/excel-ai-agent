import { CheckCircle2, LoaderCircle, Mail, Send, ShieldCheck } from 'lucide-react'
import type { FormEvent } from 'react'

interface EmailRecipientHeroProps {
  displayName: string
  email: string
  isCreating: boolean
  onDisplayNameChange: (displayName: string) => void
  onEmailChange: (email: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

const EmailRecipientHero = ({
  displayName,
  email,
  isCreating,
  onDisplayNameChange,
  onEmailChange,
  onSubmit,
}: EmailRecipientHeroProps) => (
  <section className="page-reveal page-reveal-delay-1 overflow-hidden rounded-[1.75rem] border border-brand-100 bg-gradient-to-br from-brand-700 via-brand-600 to-sky-500 text-white shadow-[0_20px_50px_rgb(37_99_235/18%)]">
    <div className="grid gap-7 p-6 md:p-8 lg:grid-cols-[1fr_24rem] lg:items-center">
      <div>
        <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[0.68rem] font-extrabold tracking-[0.12em] text-blue-50">
          <Mail size={14} /> EMAIL RECIPIENT
        </span>
        <h2 className="mt-5 text-2xl font-extrabold tracking-[-0.035em]">
          이메일 주소를 등록하세요
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-100">
          분석 결과를 받을 이메일 주소를 등록하고, 완료된 Excel 분석에서 원하는 수신자를
          선택해 전송할 수 있습니다.
        </p>
        <div className="mt-6 flex flex-wrap gap-3 text-xs font-semibold text-blue-50">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2">
            <CheckCircle2 size={14} /> 즉시 등록
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2">
            <ShieldCheck size={14} /> 내 목록만 관리
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2">
            <Send size={14} /> 수신자 선택 전송
          </span>
        </div>
      </div>

      <form
        className="rounded-[1.35rem] border border-white/30 bg-white p-5 text-slate-900 shadow-xl"
        onSubmit={onSubmit}
      >
        <label
          className="text-xs font-extrabold text-slate-700"
          htmlFor="email-recipient-name"
        >
          수신자 이름 <span className="font-medium text-slate-400">(선택)</span>
        </label>
        <input
          autoComplete="name"
          className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm font-medium outline-none transition placeholder:text-slate-300 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-50"
          disabled={isCreating}
          id="email-recipient-name"
          maxLength={255}
          onChange={(event) => onDisplayNameChange(event.target.value)}
          placeholder="예: 재무팀 김민지"
          value={displayName}
        />
        <label
          className="mt-3 block text-xs font-extrabold text-slate-700"
          htmlFor="email-recipient-address"
        >
          이메일 주소
        </label>
        <input
          autoComplete="email"
          className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm font-medium outline-none transition placeholder:text-slate-300 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-50"
          disabled={isCreating}
          id="email-recipient-address"
          maxLength={255}
          onChange={(event) => onEmailChange(event.target.value)}
          placeholder="name@company.com"
          required
          type="email"
          value={email}
        />
        <button
          className="button-primary mt-3 inline-flex h-11 w-full gap-2"
          disabled={isCreating || email.trim().length === 0}
          type="submit"
        >
          {isCreating ? (
            <LoaderCircle className="animate-spin" size={16} />
          ) : (
            <Mail size={16} />
          )}
          {isCreating ? '등록 중' : '수신자 추가'}
        </button>
      </form>
    </div>
  </section>
)

export default EmailRecipientHero
