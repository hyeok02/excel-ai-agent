import { FileSpreadsheet, LoaderCircle, X } from 'lucide-react'
import type { ChangeEvent } from 'react'

import { formatBytes } from '@/utils/analysis/analysisFile'

interface SelectedFileProps {
  file: File
  isPending: boolean
  onClearFile: () => void
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void
  onStartAnalysis: () => void
}

export const SelectedFile = ({
  file,
  isPending,
  onClearFile,
  onFileChange,
  onStartAnalysis,
}: SelectedFileProps) => (
  <div className="flex max-w-xl flex-col items-center text-center">
    <span className="grid size-16 place-items-center rounded-2xl border border-brand-100 bg-white text-brand-700 shadow-[0_10px_25px_rgb(37_99_235/12%)]">
      <FileSpreadsheet aria-hidden="true" size={26} />
    </span>
    <p className="mt-5 max-w-full truncate text-base font-extrabold text-slate-900">
      {file.name}
    </p>
    <p className="mt-1 text-sm text-slate-500">
      {formatBytes(file.size)} · 분석 준비 완료
    </p>
    <p className="mt-2 text-xs text-slate-400">
      다른 파일을 끌어놓으면 선택한 파일이 변경돼요.
    </p>
    <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
      <label className="inline-flex cursor-pointer items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm transition hover:border-brand-200 hover:text-brand-700">
        파일 변경
        <input
          accept=".xlsx,.xlsm"
          className="sr-only"
          disabled={isPending}
          onChange={onFileChange}
          type="file"
        />
      </label>
      <button
        aria-label="선택한 파일 제거"
        className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-400 shadow-sm transition hover:border-red-100 hover:text-red-500 disabled:opacity-50"
        disabled={isPending}
        onClick={onClearFile}
        type="button"
      >
        <X aria-hidden="true" size={18} />
      </button>
      <button
        className="button-primary inline-flex w-28 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isPending}
        onClick={onStartAnalysis}
        type="button"
      >
        {isPending ? (
          <>
            <LoaderCircle aria-hidden="true" className="mr-2 animate-spin" size={16} />
            분석 중
          </>
        ) : (
          '분석 시작'
        )}
      </button>
    </div>
  </div>
)

export const EmptyFilePicker = ({
  isPending,
  onFileChange,
}: {
  isPending: boolean
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void
}) => (
  <label className="flex h-full w-full cursor-pointer flex-col items-center justify-center">
    <span className="upload-icon">XLSX</span>
    <span className="mt-5 text-base font-bold text-slate-900">
      Excel 파일을 끌어놓거나 클릭하세요
    </span>
    <span className="mt-2 text-sm text-slate-500">
      .xlsx, .xlsm 형식 · 파일당 최대 50MB
    </span>
    <span className="mt-5 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white shadow-brand">
      파일 찾아보기
    </span>
    <input
      accept=".xlsx,.xlsm"
      className="sr-only"
      disabled={isPending}
      onChange={onFileChange}
      type="file"
    />
  </label>
)