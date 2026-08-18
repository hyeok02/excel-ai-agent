import { useMutation } from '@tanstack/react-query'
import {
  CheckCircle2,
  FileSpreadsheet,
  LoaderCircle,
  TriangleAlert,
  X,
} from 'lucide-react'
import {
  type ChangeEvent,
  type DragEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { type AnalysisMode, analyzeWorkbook, type SheetResult } from '@/api/analysis'
import { getErrorMessage } from '@/utils/apiClient'
import { cn } from '@/utils/cn'

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
const ALLOWED_EXTENSIONS = ['xlsx', 'xlsm']
type AnalysisFeedback = 'success' | 'error'

const formatBytes = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const validateFile = (file: File) => {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (!extension || !ALLOWED_EXTENSIONS.includes(extension)) {
    return '.xlsx 또는 .xlsm 형식의 Excel 파일만 업로드할 수 있습니다.'
  }

  if (file.size === 0) {
    return '빈 파일은 업로드할 수 없습니다.'
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return '파일 크기는 50MB를 초과할 수 없습니다.'
  }

  return null
}

const SheetResultCard = ({ sheet }: { sheet: SheetResult }) => {
  return (
    <details className="group rounded-2xl border border-slate-200 bg-white open:shadow-sm">
      <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-4 p-5 marker:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
            <FileSpreadsheet aria-hidden="true" size={18} />
          </span>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-extrabold text-slate-900">
              {sheet.name}
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              {sheet.rows.toLocaleString()}행 × {sheet.columns.toLocaleString()}열
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            영역 {sheet.regionCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            수식 {sheet.formulaCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            테이블 {sheet.tableCount}
          </span>
          <span className="rounded-lg bg-slate-50 px-2.5 py-1.5">
            차트 {sheet.chartCount}
          </span>
        </div>
      </summary>

      <div className="grid gap-5 border-t border-slate-100 p-5 lg:grid-cols-2">
        <section>
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            탐지된 영역
          </h4>
          {sheet.regions.length > 0 ? (
            <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
              {sheet.regions.map((region, index) => (
                <div
                  className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2.5 text-xs"
                  key={`${region.startCell}-${region.endCell}-${index}`}
                >
                  <span className="font-bold text-slate-700">
                    {region.startCell} : {region.endCell}
                  </span>
                  <span className="text-slate-400">
                    {region.cellCount.toLocaleString()}셀
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 rounded-xl bg-slate-50 p-4 text-xs text-slate-400">
              탐지된 데이터 영역이 없습니다.
            </p>
          )}
        </section>

        <section>
          <h4 className="text-xs font-extrabold tracking-wide text-slate-700">
            수식과 참조 관계
          </h4>
          {sheet.formulas.length > 0 ? (
            <div className="mt-3 max-h-64 space-y-2 overflow-auto pr-1">
              {sheet.formulas.map((formula) => (
                <div className="rounded-xl bg-slate-50 p-3 text-xs" key={formula.cell}>
                  <div className="flex items-start gap-2">
                    <span className="shrink-0 rounded-md bg-white px-2 py-1 font-extrabold text-brand-700 shadow-sm">
                      {formula.cell}
                    </span>
                    <code className="break-all pt-1 leading-5 text-slate-600">
                      {formula.formula}
                    </code>
                  </div>
                  <p className="mt-2 break-all text-slate-400">
                    참조:{' '}
                    {formula.references.length > 0
                      ? formula.references.join(', ')
                      : '없음'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 rounded-xl bg-slate-50 p-4 text-xs text-slate-400">
              분석할 수식이 없습니다.
            </p>
          )}
        </section>
      </div>
    </details>
  )
}

const AnalysisPage = () => {
  const [mode, setMode] = useState<AnalysisMode>('BFS')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [clientError, setClientError] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<AnalysisFeedback | null>(null)

  const analysisMutation = useMutation({
    mutationFn: ({ file, analysisMode }: { file: File; analysisMode: AnalysisMode }) =>
      analyzeWorkbook(file, analysisMode),
    onError: () => setFeedback('error'),
    onSuccess: () => setFeedback('success'),
  })

  useEffect(() => {
    if (!feedback) {
      return undefined
    }

    const timeoutId = window.setTimeout(() => setFeedback(null), 1900)
    return () => window.clearTimeout(timeoutId)
  }, [feedback])

  const analysisResult = analysisMutation.data?.result
  const workbook = analysisResult?.workbook
  const totals = useMemo(() => {
    if (!workbook) {
      return null
    }

    return workbook.sheets.reduce(
      (accumulator, sheet) => ({
        regions: accumulator.regions + sheet.regionCount,
        formulas: accumulator.formulas + sheet.formulaCount,
        tables: accumulator.tables + sheet.tableCount,
        charts: accumulator.charts + sheet.chartCount,
      }),
      { regions: 0, formulas: 0, tables: 0, charts: 0 },
    )
  }, [workbook])

  const errorMessage =
    clientError ??
    (analysisMutation.isError ? getErrorMessage(analysisMutation.error) : null)

  const status = analysisMutation.isPending
    ? 'pending'
    : analysisMutation.isSuccess
      ? 'success'
      : analysisMutation.isError
        ? 'error'
        : 'idle'

  const statusText = {
    idle: '파일 업로드 대기',
    pending: '분석 진행 중',
    success: '분석 완료',
    error: '분석 실패',
  }[status]

  const selectFile = (file: File) => {
    const validationMessage = validateFile(file)

    analysisMutation.reset()
    setClientError(validationMessage)
    setSelectedFile(validationMessage ? null : file)
    setFeedback(validationMessage ? 'error' : null)
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      selectFile(file)
    }
    event.target.value = ''
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)

    const file = event.dataTransfer.files[0]
    if (file) {
      selectFile(file)
    }
  }

  const startAnalysis = () => {
    if (!selectedFile) {
      setClientError('분석할 Excel 파일을 먼저 선택해주세요.')
      setFeedback('error')
      return
    }

    setClientError(null)
    setFeedback(null)
    analysisMutation.mutate({ file: selectedFile, analysisMode: mode })
  }

  const clearFile = () => {
    setSelectedFile(null)
    setClientError(null)
    setFeedback(null)
    analysisMutation.reset()
  }

  return (
    <div className="space-y-7">
      {feedback && (
        <div
          aria-live="assertive"
          className="analysis-feedback-overlay"
          role={feedback === 'error' ? 'alert' : 'status'}
        >
          <div className="analysis-feedback-card" data-result={feedback}>
            <span className="analysis-feedback-icon">
              {feedback === 'success' ? (
                <CheckCircle2 aria-hidden="true" size={54} strokeWidth={1.8} />
              ) : (
                <X aria-hidden="true" size={54} strokeWidth={2} />
              )}
            </span>
            <strong>{feedback === 'success' ? '분석 완료' : '분석 실패'}</strong>
            <span>
              {feedback === 'success'
                ? '결과를 성공적으로 불러왔어요'
                : '오류 내용을 확인해주세요'}
            </span>
          </div>
        </div>
      )}

      <section className="panel page-heading p-6 md:p-8">
        <div>
          <p className="eyebrow">EXCEL INTELLIGENCE</p>
          <h1 className="page-title">Excel 분석</h1>
          <p className="page-description">
            엑셀 파일을 업로드하면 시트별 리전과 수식을 탐지하고, 셀 참조 관계를
            구조화하여 화면에 표시합니다.
          </p>
        </div>
        <span className="status-pill" data-status={status}>
          <span />
          {statusText}
        </span>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
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
              disabled={analysisMutation.isPending}
              onClick={() => setMode('BFS')}
              type="button"
            >
              BFS 군집화
            </button>
            <button
              className={cn('mode-button', mode === 'LLM' && 'mode-button-active')}
              disabled={analysisMutation.isPending}
              onClick={() => setMode('LLM')}
              type="button"
            >
              LLM 직접 분석
            </button>
          </div>

          {mode === 'LLM' && (
            <p className="mt-3 text-xs text-slate-400">
              현재는 워크북 구조 분석 결과를 제공하며, LLM 인사이트 생성은 후속 단계에서
              연결됩니다.
            </p>
          )}

          <div
            className={cn(
              'upload-zone',
              selectedFile && 'upload-zone-selected',
              isDragging && 'border-brand-500 bg-brand-50',
              analysisMutation.isPending && 'pointer-events-none opacity-70',
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
                      disabled={analysisMutation.isPending}
                      onChange={handleFileChange}
                      type="file"
                    />
                  </label>
                  <button
                    aria-label="선택한 파일 제거"
                    className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-400 shadow-sm transition hover:border-red-100 hover:text-red-500 disabled:opacity-50"
                    disabled={analysisMutation.isPending}
                    onClick={clearFile}
                    type="button"
                  >
                    <X aria-hidden="true" size={18} />
                  </button>
                  <button
                    className="button-primary inline-flex w-28 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={analysisMutation.isPending}
                    onClick={startAnalysis}
                    type="button"
                  >
                    {analysisMutation.isPending ? (
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
                  disabled={analysisMutation.isPending}
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

        <aside>
          <article className="panel flex h-full flex-col p-6">
            <p className="text-xs font-bold tracking-[0.12em] text-slate-400">
              ANALYSIS FLOW
            </p>
            <h2 className="mt-2 text-base font-extrabold text-slate-950">
              분석 진행 과정
            </h2>
            <ol className="mt-5 flex flex-1 flex-col divide-y divide-slate-100">
              {[
                ['1', '파일 업로드 및 검증', '형식과 용량을 확인해요'],
                ['2', '워크북 파싱', '시트와 셀 데이터를 읽어요'],
                ['3', '시트·테이블·차트 영역 탐지', '워크북의 주요 영역을 구분해요'],
                ['4', '수식과 셀 참조 관계 분석', '수식과 연결 구조를 추적해요'],
                ['5', '분석 결과 구조화', '분석 결과와 핵심 수치를 정리해요'],
                ['6', '결과 저장 및 화면 표시', '결과를 저장하고 화면에 보여줘요'],
              ].map(([step, title, description]) => (
                <li
                  className="flex flex-1 items-center gap-3 py-3 first:pt-0 last:pb-0"
                  key={step}
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-extrabold text-brand-700">
                    {step}
                  </span>
                  <div>
                    <p className="text-sm font-bold text-slate-800">{title}</p>
                    <p className="mt-0.5 text-xs leading-5 text-slate-400">
                      {description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </article>
        </aside>
      </section>

      {workbook && totals && analysisResult && (
        <section className="panel p-5 md:p-7" aria-live="polite">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle2 aria-hidden="true" size={18} />
                <span className="text-xs font-extrabold tracking-wide">분석 완료</span>
              </div>
              <h2 className="mt-2 text-xl font-extrabold tracking-tight text-slate-950">
                {workbook.filename}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                분석 ID {analysisResult.analysisId}
              </p>
            </div>
            <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-500">
              {new Date(analysisResult.createdAt).toLocaleString('ko-KR')}
            </span>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ['시트', workbook.sheetCount],
              ['데이터 영역', totals.regions],
              ['수식', totals.formulas],
              ['테이블', totals.tables],
              ['차트', totals.charts],
            ].map(([label, value]) => (
              <div className="rounded-2xl bg-slate-50 p-4" key={label}>
                <p className="text-xs font-semibold text-slate-400">{label}</p>
                <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
                  {Number(value).toLocaleString()}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-6 space-y-3">
            {workbook.sheets.map((sheet) => (
              <SheetResultCard key={sheet.name} sheet={sheet} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export default AnalysisPage
