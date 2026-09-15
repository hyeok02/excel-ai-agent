import { CheckCircle2, FileSpreadsheet, X } from 'lucide-react'
import type { ChangeEvent } from 'react'

import { formatBytes } from '@/utils/analysis/analysisFile'

export interface RestoredAnalysisFile {
  name: string
  sizeBytes: number
}

interface RestoredFilePickerProps {
  file: RestoredAnalysisFile
  isPending: boolean
  onClearFile: () => void
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void
}

/**
 * 이력에서 불러왔거나 새로고침으로 복원한 분석을 보여준다.
 *
 * 복원된 분석은 결과만 남고 File 객체는 되살릴 수 없다. 그렇다고 빈 업로드
 * 칸을 두면 '파일을 고르세요'와 '분석 완료'가 한 화면에 같이 뜬다.
 */
const RestoredFilePicker = ({
  file,
  isPending,
  onClearFile,
  onFileChange,
}: RestoredFilePickerProps) => (
  <div className="flex max-w-xl flex-col items-center text-center">
    <span className="grid size-16 place-items-center rounded-2xl border border-emerald-100 bg-white text-emerald-600 shadow-[0_10px_25px_rgb(16_185_129/12%)]">
      <FileSpreadsheet aria-hidden="true" size={26} />
    </span>
    <p className="mt-5 max-w-full truncate text-base font-extrabold text-slate-900">
      {file.name}
    </p>
    <p className="mt-1 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600">
      <CheckCircle2 aria-hidden="true" size={15} />
      불러온 분석 결과
    </p>
    <p className="mt-1 text-sm text-slate-500">
      {formatBytes(file.sizeBytes)} · 아래에서 결과를 확인할 수 있어요
    </p>
    <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
      <label className="inline-flex cursor-pointer items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm transition hover:border-brand-200 hover:text-brand-700">
        새 파일 분석
        <input
          accept=".xlsx,.xlsm"
          className="sr-only"
          disabled={isPending}
          onChange={onFileChange}
          type="file"
        />
      </label>
      <button
        aria-label="불러온 분석 닫기"
        className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-400 shadow-sm transition hover:border-red-100 hover:text-red-500 disabled:opacity-50"
        disabled={isPending}
        onClick={onClearFile}
        type="button"
      >
        <X aria-hidden="true" size={18} />
      </button>
    </div>
  </div>
)

export default RestoredFilePicker
