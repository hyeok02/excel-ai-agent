import { FileSpreadsheet, LoaderCircle, TriangleAlert, X } from 'lucide-react'
import { type ChangeEvent, type DragEvent, useState } from 'react'

import type { AnalysisMode } from '@/api/analysis'
import { formatBytes } from '@/utils/analysisFile'
import { cn } from '@/utils/cn'

interface AnalysisUploadPanelProps {
  errorMessage: string | null
  isPending: boolean
  mode: AnalysisMode
  onClearFile: () => void
  onModeChange: (mode: AnalysisMode) => void
  onSelectFile: (file: File) => void
  onStartAnalysis: () => void
  selectedFile: File | null
}

const AnalysisUploadPanel = ({
  errorMessage,
  isPending,
  mode,
  onClearFile,
  onModeChange,
  onSelectFile,
  onStartAnalysis,
  selectedFile,
}: AnalysisUploadPanelProps) => {
  const [isDragging, setIsDragging] = useState(false)

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      onSelectFile(file)
    }
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)

    const file = event.dataTransfer.files[0]
    if (file) {
      onSelectFile(file)
    }
  }

  return (
    <article className="panel p-5 md:p-7">
      <div>
        <h2 className="text-xl font-extrabold tracking-tight text-slate-950">
          분석할 파일을 선택하세요
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          분석 결과는 분석 ID와 함께 저장되며 이후 다시 조회할 수 있어요.
        </p>
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-2 rounded-2xl bg-slate-50 p-2">
        <span className="mr-2 pl-2 text-sm font-bold text-slate-700">분석 모드</span>
        <button
          className={cn('mode-button', mode === 'BFS' && 'mode-button-active')}
          disabled={isPending}
          onClick={() => onModeChange('BFS')}
          type="button"
        >
          BFS 군집화
        </button>
        <button
          className={cn('mode-button', mode === 'LLM' && 'mode-button-active')}
          disabled={isPending}
          onClick={() => onModeChange('LLM')}
          type="button"
        >
          LLM 직접 분석
        </button>
      </div>

      <div
        className={cn(
          'upload-zone',
          selectedFile && 'upload-zone-selected',
          isDragging && 'border-brand-500 bg-brand-50',
          isPending && 'pointer-events-none opacity-70',
        )}
        onDragEnter={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setIsDragging(false)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        {selectedFile ? (
          <div className="flex max-w-xl flex-col items-center text-center">
            <span className="grid size-16 place-items-center rounded-2xl border border-brand-100 bg-white text-brand-700 shadow-[0_10px_25px_rgb(37_99_235/12%)]">
              <FileSpreadsheet aria-hidden="true" size={26} />
            </span>
            <p className="mt-5 max-w-full truncate text-base font-extrabold text-slate-900">
              {selectedFile.name}
            </p>
            <p className="mt-1 text-sm text-slate-500">
              {formatBytes(selectedFile.size)} · 분석 준비 완료
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
                  onChange={handleFileChange}
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
                    <LoaderCircle
                      aria-hidden="true"
                      className="mr-2 animate-spin"
                      size={16}
                    />
                    분석 중
                  </>
                ) : (
                  '분석 시작'
                )}
              </button>
            </div>
          </div>
        ) : (
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
              onChange={handleFileChange}
              type="file"
            />
          </label>
        )}
      </div>

      {errorMessage && (
        <div
          className="mt-4 flex items-start gap-3 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-700"
          role="alert"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 shrink-0" size={17} />
          <p>{errorMessage}</p>
        </div>
      )}
    </article>
  )
}

export default AnalysisUploadPanel
