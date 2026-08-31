import { FilePenLine, Send, ShieldCheck, TriangleAlert } from 'lucide-react'
import type { FormEvent } from 'react'
import { useState } from 'react'

import WritebackProposalCard from '@/components/analysis/result/writeback/WritebackProposalCard'
import { useWorkbookWritebacks } from '@/hooks/analysis/useWorkbookWritebacks'

const WorkbookWritebackSection = ({ analysisId }: { analysisId: string }) => {
  const writebacks = useWorkbookWritebacks(analysisId)
  const [instruction, setInstruction] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const normalized = instruction.trim()
    if (normalized.length < 2 || writebacks.isProposing) return
    await writebacks.propose(normalized)
    setInstruction('')
  }
  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white p-5 shadow-sm md:p-7">
      <p className="flex items-center gap-2 text-xs font-extrabold tracking-[0.14em] text-brand-700">
        <FilePenLine size={16} /> APPROVAL-BASED EXCEL UPDATE
      </p>
      <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">승인 후 Excel 수정</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        바꿀 내용을 말하면 원본 셀의 전·후 값을 먼저 보여줍니다. 승인 전에는 파일을 수정하지 않으며, 승인 후에도 원본이 아닌 복사본만 만듭니다.
      </p>
      <div className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
        <ShieldCheck className="shrink-0 text-brand-600" size={19} />
        수식 셀 덮어쓰기와 새 수식 입력은 차단하고, 수정 후 수식·서식·병합·매크로 보존 여부를 다시 검사합니다.
      </div>
      <form className="mt-5" onSubmit={(event) => void submit(event)}>
        <textarea className="min-h-28 w-full resize-y rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-800 shadow-sm outline-none transition focus:border-brand-400 focus:ring-4 focus:ring-brand-50" maxLength={1000} onChange={(event) => setInstruction(event.target.value)} placeholder="예: 매출현황 시트 B2의 값을 12로 수정해줘" value={instruction} />
        <div className="mt-3 flex justify-end">
          <button className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300" disabled={instruction.trim().length < 2 || writebacks.isProposing} type="submit">
            <Send size={16} /> {writebacks.isProposing ? '원본 셀 확인 중…' : '변경 제안 만들기'}
          </button>
        </div>
      </form>
      {writebacks.errorMessage && (
        <div className="mt-4 flex gap-2 rounded-2xl bg-red-50 p-4 text-sm text-red-700" role="alert"><TriangleAlert className="shrink-0" size={17} /> {writebacks.errorMessage}</div>
      )}
      {writebacks.items.map((item) => (
        <WritebackProposalCard
          isPending={writebacks.pendingId === item.writebackId}
          item={item}
          key={`${item.writebackId}-${item.status}`}
          onApprove={() => writebacks.approve(item.writebackId)}
          onDownload={() => writebacks.download(item.writebackId)}
          onReject={() => writebacks.reject(item.writebackId)}
        />
      ))}
    </section>
  )
}

export default WorkbookWritebackSection
