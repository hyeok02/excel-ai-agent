import type { AnalysisDepth, AnalysisMode } from '@/api/analysis'
import { cn } from '@/utils/cn'

interface AnalysisOptionsProps {
  depth: AnalysisDepth
  isPending: boolean
  mode: AnalysisMode
  onDepthChange: (depth: AnalysisDepth) => void
  onModeChange: (mode: AnalysisMode) => void
}

const DEPTH_OPTIONS = [
  ['AUTO', '자동'],
  ['FAST', '빠른'],
  ['PRECISE', '정밀'],
] as const

const AnalysisOptions = ({
  depth,
  isPending,
  mode,
  onDepthChange,
  onModeChange,
}: AnalysisOptionsProps) => (
  <div className="mt-7 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-slate-50 p-2">
    <div className="flex flex-wrap items-center gap-2">
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
        'flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-100 bg-white p-1 transition-opacity',
        mode !== 'LLM' && 'opacity-40',
      )}
      title={mode === 'LLM' ? undefined : 'LLM 직접 분석에서 사용할 수 있어요.'}
    >
      <span className="px-2 text-xs font-bold text-slate-500">LLM 분석 깊이</span>
      {DEPTH_OPTIONS.map(([value, label]) => (
        <button
          aria-pressed={mode === 'LLM' && depth === value}
          className={cn(
            'rounded-lg px-3 py-2 text-xs font-bold transition',
            mode === 'LLM' && depth === value
              ? 'bg-brand-50 text-brand-700 shadow-sm'
              : 'text-slate-500',
          )}
          disabled={isPending || mode !== 'LLM'}
          key={value}
          onClick={() => onDepthChange(value)}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  </div>
)

export default AnalysisOptions
