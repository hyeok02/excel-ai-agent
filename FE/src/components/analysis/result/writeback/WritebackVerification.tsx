import { CheckCircle2, Download, LoaderCircle, XCircle } from 'lucide-react'

import type { WorkbookWriteback } from '@/api/analysis'

interface Props {
  item: WorkbookWriteback
  isDownloading: boolean
  downloadedFilename?: string
  onDownload: () => void
}

const WritebackVerification = ({
  item,
  isDownloading,
  downloadedFilename,
  onDownload,
}: Props) => {
  if (!item.verification) return null
  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h4 className="flex items-center gap-2 text-sm font-extrabold text-emerald-800">
        <CheckCircle2 size={17} /> 복사본 수정 및 최종 검증 완료
      </h4>
      <p className="mt-2 text-xs leading-5 text-slate-600">
        승인한 값 반영과 수식·서식·병합·매크로 보존을 확인했습니다.
      </p>
      <details className="mt-2 text-xs text-slate-500">
        <summary className="cursor-pointer font-bold">
          검증 항목 {item.verification.checks.length}개 보기
        </summary>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {item.verification.checks.map((check) => (
            <div
              className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2"
              key={check.name}
            >
              {check.passed ? (
                <CheckCircle2 className="text-emerald-600" size={14} />
              ) : (
                <XCircle className="text-red-500" size={14} />
              )}
              {check.detail}
            </div>
          ))}
        </div>
      </details>
      <p className="mt-3 text-xs text-slate-500">
        원본은 그대로 보관되며, 승인자 {item.approvedBy ?? '-'}의 감사 이력이
        저장되었습니다.
      </p>
      <button
        className="mt-4 inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-emerald-800 disabled:cursor-wait disabled:bg-emerald-300"
        disabled={isDownloading}
        onClick={onDownload}
        type="button"
      >
        {isDownloading ? (
          <LoaderCircle className="animate-spin" size={16} />
        ) : (
          <Download size={16} />
        )}
        {isDownloading ? '수정본 다운로드 중…' : '검증된 수정본 다운로드'}
      </button>
      {downloadedFilename && (
        <p
          className="mt-3 flex items-center gap-2 text-xs font-bold text-emerald-700"
          role="status"
        >
          <CheckCircle2 size={15} /> {downloadedFilename} 다운로드 완료
        </p>
      )}
    </div>
  )
}

export default WritebackVerification
