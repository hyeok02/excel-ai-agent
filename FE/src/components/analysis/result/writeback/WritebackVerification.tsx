import { CheckCircle2, Download, XCircle } from 'lucide-react'

import type { WorkbookWriteback } from '@/api/analysis'

interface Props {
  item: WorkbookWriteback
  isPending: boolean
  onDownload: () => void
}

const WritebackVerification = ({ item, isPending, onDownload }: Props) => {
  if (!item.verification) return null
  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 className="flex items-center gap-2 text-sm font-extrabold text-emerald-800">
        <CheckCircle2 size={17} /> 복사본 수정 및 최종 검증 완료
      </h4>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {item.verification.checks.map((check) => (
          <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2 text-xs font-bold text-slate-600" key={check.name}>
            {check.passed ? <CheckCircle2 className="text-emerald-600" size={15} /> : <XCircle className="text-red-500" size={15} />}
            {check.detail}
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        원본은 그대로 보관되며, 승인자 {item.approvedBy ?? '-'}의 감사 이력이 저장되었습니다.
      </p>
      <button className="mt-4 inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-emerald-800 disabled:cursor-wait disabled:bg-emerald-300" disabled={isPending} onClick={onDownload} type="button">
        <Download size={16} /> 검증된 수정본 다운로드
      </button>
    </div>
  )
}

export default WritebackVerification
