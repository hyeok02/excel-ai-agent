import { Ban, CheckCircle2, LoaderCircle, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'

import type { WorkbookWriteback } from '@/api/analysis'
import WritebackChangeList from '@/components/analysis/result/writeback/WritebackChangeList'
import { WRITEBACK_STATUS_PRESENTATION } from '@/components/analysis/result/writeback/writebackPresentation'
import WritebackVerification from '@/components/analysis/result/writeback/WritebackVerification'

interface Props {
  item: WorkbookWriteback
  pendingAction: 'approve' | 'reject' | 'download' | null
  downloadedFilename?: string
  onApprove: () => Promise<unknown>
  onRetry: () => void
  onReject: () => Promise<unknown>
  onDownload: () => void
}

const WritebackProposalCard = ({
  item,
  pendingAction,
  downloadedFilename,
  onApprove,
  onRetry,
  onReject,
  onDownload,
}: Props) => {
  const [confirmed, setConfirmed] = useState(false)
  const proposed = item.status === 'PROPOSED'
  const blocked = item.status === 'BLOCKED'
  const failed = item.status === 'FAILED'
  const isPending = pendingAction !== null
  const status = WRITEBACK_STATUS_PRESENTATION[item.status]

  return (
    <article className="mt-5 rounded-3xl border border-slate-200 bg-slate-50/60 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold text-slate-400">요청: {item.instruction}</p>
          <h3 className="mt-1 text-base font-extrabold text-slate-900">
            {item.proposal.summary}
          </h3>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-extrabold ${status.style}`}>
          {status.label}
        </span>
      </div>
      {item.proposal.changes.length > 0 && (
        <WritebackChangeList changes={item.proposal.changes} />
      )}
      {item.proposal.risks.length > 0 && (
        <div
          className={`mt-4 rounded-2xl p-4 text-sm ${proposed ? 'bg-amber-50 text-amber-800' : 'bg-red-50 text-red-700'}`}
        >
          <p className="flex items-center gap-2 font-extrabold">
            <Ban size={16} /> {proposed ? '제안에서 제외한 항목' : '변경이 차단된 이유'}
          </p>
          {item.proposal.risks.map((reason) => (
            <p className="mt-1 text-xs" key={reason}>
              • {reason}
            </p>
          ))}
        </div>
      )}
      {item.status !== 'APPLIED' && item.proposal.limitations.length > 0 && (
        <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-extrabold">변경 제안 범위 안내</p>
          {item.proposal.limitations.map((reason) => (
            <p className="mt-1 text-xs" key={reason}>
              • {reason}
            </p>
          ))}
        </div>
      )}
      {proposed && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          <label className="flex cursor-pointer items-start gap-3 text-sm font-semibold text-slate-700">
            <input
              checked={confirmed}
              className="mt-0.5 h-4 w-4 accent-brand-600"
              onChange={(event) => setConfirmed(event.target.checked)}
              type="checkbox"
            />
            원본 값과 변경 값을 확인했으며, 원본이 아닌 복사본 수정을 승인합니다.
          </label>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
              disabled={!confirmed || isPending}
              onClick={() => void onApprove().catch(() => undefined)}
              type="button"
            >
              {pendingAction === 'approve' ? (
                <LoaderCircle className="animate-spin" size={16} />
              ) : (
                <ShieldCheck size={16} />
              )}
              {pendingAction === 'approve'
                ? '복사본 수정 및 검증 중…'
                : '승인하고 수정본 만들기'}
            </button>
            <button
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-600 disabled:opacity-40"
              disabled={isPending}
              onClick={() => void onReject().catch(() => undefined)}
              type="button"
            >
              {pendingAction === 'reject' ? (
                <LoaderCircle className="animate-spin" size={16} />
              ) : (
                <X size={16} />
              )}
              {pendingAction === 'reject' ? '거절 처리 중…' : '거절'}
            </button>
          </div>
        </div>
      )}
      {(blocked || failed) && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          {failed && (
            <p className="mb-3 text-sm font-semibold text-red-700">
              수정본을 만들지 못했습니다. 요청 내용을 확인한 후 다시 시도해주세요.
            </p>
          )}
          <button
            className="inline-flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-4 py-2.5 text-sm font-extrabold text-brand-700 transition hover:bg-brand-50"
            onClick={onRetry}
            type="button"
          >
            <RefreshCw size={16} /> 요청 수정해서 다시 시도
          </button>
        </div>
      )}
      {item.status === 'REJECTED' && (
        <p className="mt-4 flex items-center gap-2 text-sm font-bold text-slate-500">
          <CheckCircle2 size={16} /> 파일은 변경되지 않았습니다.
        </p>
      )}
      <WritebackVerification
        downloadedFilename={downloadedFilename}
        isDownloading={pendingAction === 'download'}
        item={item}
        onDownload={onDownload}
      />
    </article>
  )
}

export default WritebackProposalCard
