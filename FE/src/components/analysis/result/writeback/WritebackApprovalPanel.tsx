import { LoaderCircle, ShieldCheck, TriangleAlert, X } from 'lucide-react'
import { useState } from 'react'

import { approvalButtonLabel } from '@/components/analysis/result/writeback/writebackSelection'

interface Props {
  actionsDisabled: boolean
  brokenCells: string[]
  pendingAction: 'approve' | 'reject' | 'download' | null
  selectedCount: number
  totalCount: number
  onApprove: () => void
  onReject: () => void
}

const WritebackApprovalPanel = ({
  actionsDisabled,
  brokenCells,
  pendingAction,
  selectedCount,
  totalCount,
  onApprove,
  onReject,
}: Props) => {
  const [confirmed, setConfirmed] = useState(false)
  const nothingSelected = totalCount > 0 && selectedCount === 0

  return (
    <div className="mt-4 border-t border-slate-200 pt-4">
      {brokenCells.length > 0 && (
        <div className="mb-3 flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
          <TriangleAlert className="mt-0.5 shrink-0" size={17} />
          <div>
            <p className="font-extrabold">함께 승인해야 하는 변경이 있습니다</p>
            <p className="mt-0.5 text-xs">
              {brokenCells.join(' · ')} 은(는) 선택하지 않은 변경의 셀을 참조합니다.
              이대로 승인하면 이 셀의 계산 결과가 위 미리보기와 달라집니다.
            </p>
          </div>
        </div>
      )}
      <label className="flex cursor-pointer items-start gap-3 text-sm font-semibold text-slate-700">
        <input
          checked={confirmed}
          className="mt-0.5 h-4 w-4 accent-brand-600"
          disabled={actionsDisabled}
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        원본 값과 변경 값을 확인했으며, 원본이 아닌 복사본 수정을 승인합니다.
      </label>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          disabled={
            actionsDisabled || !confirmed || nothingSelected || pendingAction !== null
          }
          onClick={onApprove}
          type="button"
        >
          {pendingAction === 'approve' ? (
            <LoaderCircle className="animate-spin" size={16} />
          ) : (
            <ShieldCheck size={16} />
          )}
          {pendingAction === 'approve'
            ? '복사본 수정 및 검증 중…'
            : approvalButtonLabel(selectedCount, totalCount)}
        </button>
        <button
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-600 disabled:opacity-40"
          disabled={actionsDisabled || pendingAction !== null}
          onClick={onReject}
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
      {nothingSelected && (
        <p className="mt-2 text-xs font-semibold text-slate-500">
          적용할 변경을 하나 이상 선택해주세요.
        </p>
      )}
    </div>
  )
}

export default WritebackApprovalPanel
