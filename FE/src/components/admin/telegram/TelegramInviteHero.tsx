import { Link2, LoaderCircle, Send, UserCheck, UserPlus } from 'lucide-react'
import type { FormEvent } from 'react'

interface TelegramInviteHeroProps {
  isCreating: boolean
  label: string
  onLabelChange: (label: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

const TelegramInviteHero = ({
  isCreating,
  label,
  onLabelChange,
  onSubmit,
}: TelegramInviteHeroProps) => (
  <section className="page-reveal page-reveal-delay-1 overflow-hidden rounded-[1.75rem] border border-brand-100 bg-gradient-to-br from-brand-700 via-brand-600 to-sky-500 text-white shadow-[0_20px_50px_rgb(37_99_235/18%)]">
    <div className="grid gap-7 p-6 md:p-8 lg:grid-cols-[1fr_24rem] lg:items-center">
      <div>
        <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[0.68rem] font-extrabold tracking-[0.12em] text-blue-50">
          <UserPlus size={14} /> RECIPIENT INVITE
        </span>
        <h2 className="mt-5 text-2xl font-extrabold tracking-[-0.035em]">
          초대 링크 하나로 연결하세요
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-100">
          링크를 받은 사람이 텔레그램에서 봇의 시작 버튼을 누르면 수신자로 등록됩니다.
          전화번호나 텔레그램 비밀번호는 필요하지 않습니다.
        </p>
        <div className="mt-6 flex flex-wrap gap-3 text-xs font-semibold text-blue-50">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2">
            <Link2 size={14} /> 일회용 초대 링크
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2">
            <UserCheck size={14} /> 본인 동의 후 연결
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
        <label className="text-xs font-extrabold text-slate-700" htmlFor="invite-label">
          초대 구분 이름 <span className="font-medium text-slate-400">(선택)</span>
        </label>
        <input
          className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm font-medium outline-none transition placeholder:text-slate-300 focus:border-brand-400 focus:bg-white focus:ring-4 focus:ring-brand-50"
          id="invite-label"
          maxLength={60}
          onChange={(event) => onLabelChange(event.target.value)}
          placeholder="예: 재무팀 김민지"
          value={label}
        />
        <button
          className="button-primary mt-3 inline-flex h-11 w-full gap-2"
          disabled={isCreating}
          type="submit"
        >
          {isCreating ? (
            <LoaderCircle className="animate-spin" size={16} />
          ) : (
            <Link2 size={16} />
          )}
          초대 링크 만들기
        </button>
        <p className="mt-3 text-[0.7rem] leading-5 text-slate-400">
          보안을 위해 링크 주소는 생성 직후 한 번만 표시됩니다.
        </p>
      </form>
    </div>
  </section>
)

export default TelegramInviteHero
