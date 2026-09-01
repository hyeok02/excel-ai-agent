import { Check, CircleAlert, LoaderCircle } from 'lucide-react'

import type { AnalysisStatus } from '@/api/analysis'
import type { AnalysisViewStatus } from '@/hooks/analysis/useWorkbookAnalysis'
import { cn } from '@/utils/cn'

const ANALYSIS_STEPS = [
  ['파일 업로드 및 검증', '형식과 용량을 확인해요'],
  ['워크북 파싱', '시트와 셀 데이터를 읽어요'],
  ['주요 영역 탐지', '시트·테이블·차트를 구분해요'],
  ['수식 연결 분석', '수식과 셀 참조 관계를 추적해요'],
  ['결과·인사이트 구조화', '핵심 현황과 근거를 정리해요'],
  ['결과 저장 및 표시', '결과를 저장하고 화면에 보여줘요'],
] as const

type StepState = 'waiting' | 'active' | 'complete' | 'error'

interface AnalysisFlowPanelProps {
  activeStep: number
  processingStatus: AnalysisStatus | null
  status: AnalysisViewStatus
}

const getStepState = (
  step: number,
  activeStep: number,
  status: AnalysisViewStatus,
): StepState => {
  if (status === 'success' || step < activeStep) return 'complete'
  if (step !== activeStep) return 'waiting'
  return status === 'error' ? 'error' : 'active'
}

const StepIcon = ({ state, step }: { state: StepState; step: number }) => {
  if (state === 'complete') return <Check aria-hidden="true" size={15} strokeWidth={3} />
  if (state === 'error') return <CircleAlert aria-hidden="true" size={16} />
  if (state === 'active') {
    return <LoaderCircle aria-hidden="true" className="animate-spin" size={16} />
  }
  return <>{step}</>
}

const AnalysisFlowPanel = ({
  activeStep,
  processingStatus,
  status,
}: AnalysisFlowPanelProps) => {
  const isComplete = status === 'success'
  const progress = isComplete
    ? 100
    : Math.round((activeStep / ANALYSIS_STEPS.length) * 100)
  const stateLabel = isComplete
    ? '모든 단계 완료'
    : status === 'error'
      ? `${activeStep || 1}단계에서 중단`
      : activeStep
        ? `${activeStep} / ${ANALYSIS_STEPS.length} 단계`
        : '파일 선택 대기'

  return (
    <article className="panel flex h-full flex-col overflow-hidden p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold tracking-[0.12em] text-slate-400">분석 단계</p>
          <h2 className="mt-2 text-base font-extrabold text-slate-950">분석 진행 과정</h2>
        </div>
        <span className="rounded-full bg-brand-50 px-2.5 py-1 text-[10px] font-extrabold text-brand-700">
          {stateLabel}
        </span>
      </div>

      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-600 to-sky-400 transition-all duration-700"
          style={{ width: `${progress}%` }}
        />
      </div>

      <ol className="mt-4 flex flex-1 flex-col gap-1.5">
        {ANALYSIS_STEPS.map(([title, description], index) => {
          const step = index + 1
          const stepState = getStepState(step, activeStep, status)
          const isReady = step === 1 && status === 'idle' && activeStep === 1
          return (
            <li
              aria-current={stepState === 'active' ? 'step' : undefined}
              className={cn(
                'flex flex-1 items-center gap-3 rounded-xl border border-transparent px-2.5 py-2 transition-all duration-300',
                stepState === 'active' && 'border-brand-100 bg-brand-50/80 shadow-sm',
                stepState === 'error' && 'border-red-100 bg-red-50',
              )}
              key={title}
            >
              <span
                className={cn(
                  'grid size-8 shrink-0 place-items-center rounded-full text-xs font-extrabold transition-colors',
                  stepState === 'waiting' && 'bg-slate-100 text-slate-400',
                  stepState === 'active' && 'bg-brand-600 text-white shadow-brand',
                  stepState === 'complete' && 'bg-emerald-500 text-white',
                  stepState === 'error' && 'bg-red-500 text-white',
                )}
              >
                {isReady ? (
                  <Check aria-hidden="true" size={15} strokeWidth={3} />
                ) : (
                  <StepIcon state={stepState} step={step} />
                )}
              </span>
              <div className="min-w-0">
                <p
                  className={cn(
                    'text-sm font-bold',
                    stepState === 'waiting' ? 'text-slate-500' : 'text-slate-900',
                  )}
                >
                  {title}
                </p>
                <p className="mt-0.5 text-xs leading-4 text-slate-400">
                  {isReady ? '파일 확인 완료 · 분석 시작을 기다려요' : description}
                </p>
              </div>
            </li>
          )
        })}
      </ol>

      {processingStatus === 'QUEUED' && (
        <p className="mt-3 text-center text-[11px] font-semibold text-brand-600">
          서버 작업 순서를 기다리고 있어요
        </p>
      )}
    </article>
  )
}

export default AnalysisFlowPanel
