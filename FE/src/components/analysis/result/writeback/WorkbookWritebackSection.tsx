import { ChevronDown, FilePenLine, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useRef, useState } from 'react'

import WritebackComposer from '@/components/analysis/result/writeback/WritebackComposer'
import WritebackProposalCard from '@/components/analysis/result/writeback/WritebackProposalCard'
import { useWorkbookWritebacks } from '@/hooks/analysis/useWorkbookWritebacks'

const WorkbookWritebackSection = ({ analysisId }: { analysisId: string }) => {
  const writebacks = useWorkbookWritebacks(analysisId)
  const [instruction, setInstruction] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const activeItems = writebacks.items.filter((item) => item.status === 'PROPOSED')
  const latestItem = writebacks.items[0]
  const visibleIds = new Set([
    ...(latestItem ? [latestItem.writebackId] : []),
    ...activeItems.map((item) => item.writebackId),
  ])
  const currentItems = writebacks.items.filter((item) => visibleIds.has(item.writebackId))
  const historyItems = writebacks.items.filter(
    (item) => !visibleIds.has(item.writebackId),
  )

  const submit = async () => {
    const normalized = instruction.trim()
    if (normalized.length < 2 || writebacks.isProposing) return
    try {
      const result = await writebacks.propose(normalized)
      if (result.status !== 'BLOCKED') setInstruction('')
    } catch {
      // The mutation error is rendered in the section alert.
    }
  }

  const retry = (value: string) => {
    setInstruction(value)
    window.requestAnimationFrame(() => {
      textareaRef.current?.focus()
      textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }

  const proposalCard = (item: (typeof writebacks.items)[number]) => {
    const pendingAction =
      writebacks.pendingId === item.writebackId ? writebacks.pendingAction : null
    const downloadedFilename =
      writebacks.downloadNotice?.writebackId === item.writebackId
        ? writebacks.downloadNotice.filename
        : undefined
    return (
      <WritebackProposalCard
        downloadedFilename={downloadedFilename}
        item={item}
        key={`${item.writebackId}-${item.status}`}
        onApprove={() => writebacks.approve(item.writebackId)}
        onDownload={() => writebacks.download(item.writebackId)}
        onReject={() => writebacks.reject(item.writebackId)}
        onRetry={() => retry(item.instruction)}
        pendingAction={pendingAction}
      />
    )
  }

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white p-5 shadow-sm md:p-7">
      <p className="flex items-center gap-2 text-xs font-extrabold tracking-[0.14em] text-brand-700">
        <FilePenLine size={16} /> 승인 기반 Excel 수정
      </p>
      <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
        승인 후 Excel 수정
      </h2>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        바꿀 내용을 말하면 원본 셀의 전·후 값을 먼저 보여줍니다. 승인 전에는 파일을
        수정하지 않으며, 승인 후에도 원본이 아닌 복사본만 만듭니다.
      </p>
      <div className="mt-4 flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
        <ShieldCheck className="shrink-0 text-brand-600" size={19} />
        <div>
          <p className="font-extrabold text-slate-700">
            값·범위·수식을 한 번에 수정할 수 있어요
          </p>
          <p className="mt-1">
            최대 50개 셀과 여러 시트를 지원합니다. 숫자·날짜·텍스트 변경, 셀 비우기,
            요청에 직접 적은 수식을 적용할 수 있습니다.
          </p>
          <p className="mt-1 text-slate-500">
            외부 연결 수식은 제외하고, 승인 후 원본이 아닌 복사본의 보존 상태를
            검증합니다.
          </p>
        </div>
      </div>
      <WritebackComposer
        instruction={instruction}
        isPending={writebacks.isProposing}
        onChange={setInstruction}
        onSubmit={() => void submit()}
        textareaRef={textareaRef}
      />
      {writebacks.errorMessage && (
        <div
          className="mt-4 flex gap-2 rounded-2xl bg-red-50 p-4 text-sm text-red-700"
          role="alert"
        >
          <TriangleAlert className="shrink-0" size={17} /> {writebacks.errorMessage}
        </div>
      )}
      {writebacks.isLoading && (
        <p className="mt-5 text-sm font-semibold text-slate-500" role="status">
          변경 작업 기록을 불러오는 중…
        </p>
      )}
      {!writebacks.isLoading && currentItems.map(proposalCard)}
      {historyItems.length > 0 && (
        <details className="group mt-5 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-extrabold text-slate-700">
            이전 변경 기록 {historyItems.length}건
            <ChevronDown
              className="text-slate-400 transition group-open:rotate-180"
              size={18}
            />
          </summary>
          <div className="mt-2">{historyItems.map(proposalCard)}</div>
        </details>
      )}
    </section>
  )
}

export default WorkbookWritebackSection
