import { Ban, CheckCircle2, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'

import type { WorkbookWriteback } from '@/api/analysis'
import WritebackChangeList from '@/components/analysis/result/writeback/WritebackChangeList'
import WritebackVerification from '@/components/analysis/result/writeback/WritebackVerification'

interface Props {
  item: WorkbookWriteback
  isPending: boolean
  onApprove: () => Promise<unknown>
  onReject: () => Promise<unknown>
  onDownload: () => void
}

const WritebackProposalCard = ({ item, isPending, onApprove, onReject, onDownload }: Props) => {
  const [confirmed, setConfirmed] = useState(false)
  const proposed = item.status === 'PROPOSED'
  const blocked = item.status === 'BLOCKED'

  return (
    <article className="mt-5 rounded-3xl border border-slate-200 bg-slate-50/60 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-slate-400">요청: {item.instruction}</p>
          <h3 className="mt-1 text-base font-extrabold text-slate-900">{item.proposal.summary}</h3>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-extrabold ${blocked ? 'bg-red-50 text-red-700' : item.status === 'APPLIED' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
          {blocked ? '안전 기준으로 차단' : item.status === 'APPLIED' ? '적용·검증 완료' : item.status === 'REJECTED' ? '사용자 거절' : '승인 대기'}
        </span>
      </div>
      {item.proposal.changes.length > 0 && <WritebackChangeList changes={item.proposal.changes} />}
      {item.proposal.risks.length > 0 && (
        <div className="mt-4 rounded-2xl bg-red-50 p-4 text-sm text-red-700">
          <p className="flex items-center gap-2 font-extrabold"><Ban size={16} /> 변경이 차단된 이유</p>
          {item.proposal.risks.map((reason) => <p className="mt-1 text-xs" key={reason}>• {reason}</p>)}
        </div>
      )}
      {item.status !== 'APPLIED' && item.proposal.limitations.length > 0 && (
        <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-extrabold">변경 제안 범위 안내</p>
          {item.proposal.limitations.map((reason) => <p className="mt-1 text-xs" key={reason}>• {reason}</p>)}
        </div>
      )}
      {proposed && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          <label className="flex cursor-pointer items-start gap-3 text-sm font-semibold text-slate-700">
            <input checked={confirmed} className="mt-0.5 h-4 w-4 accent-brand-600" onChange={(event) => setConfirmed(event.target.checked)} type="checkbox" />
            원본 값과 변경 값을 확인했으며, 원본이 아닌 복사본 수정을 승인합니다.
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300" disabled={!confirmed || isPending} onClick={() => void onApprove()} type="button"><ShieldCheck size={16} /> 승인하고 수정본 만들기</button>
            <button className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-600 disabled:opacity-40" disabled={isPending} onClick={() => void onReject()} type="button"><X size={16} /> 거절</button>
          </div>
        </div>
      )}
      {item.status === 'REJECTED' && <p className="mt-4 flex items-center gap-2 text-sm font-bold text-slate-500"><CheckCircle2 size={16} /> 파일은 변경되지 않았습니다.</p>}
      <WritebackVerification item={item} isPending={isPending} onDownload={onDownload} />
    </article>
  )
}

export default WritebackProposalCard
