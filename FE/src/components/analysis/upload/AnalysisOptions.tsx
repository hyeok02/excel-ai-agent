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
  <div className="mt-7 flex flex-wrap items-center gap-3 rounded-2xl bg-slate-50 p-2.5">
    <fieldset className="flex min-w-0 flex-1 items-center gap-3">
      <legend className="sr-only">분석 방식</legend>
      <div className="shrink-0 pl-1">
        <p className="text-xs font-extrabold text-slate-500">분석 방식</p>
      </div>
      <div className="inline-flex min-w-0 items-center rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-100">
        <button
          aria-pressed={mode === 'BFS'}
          className={cn(
            'rounded-lg px-4 py-2 text-xs font-bold transition',
            mode === 'BFS'
              ? 'bg-brand-50 text-brand-700'
              : 'text-slate-500 hover:text-slate-700',
          )}
          disabled={isPending}
          onClick={() => onModeChange('BFS')}
          type="button"
        >
          BFS 군집화
        </button>
        <button
          aria-pressed={mode === 'LLM'}
          className={cn(
            'rounded-lg px-4 py-2 text-xs font-bold transition',
            mode === 'LLM'
              ? 'bg-brand-50 text-brand-700'
              : 'text-slate-500 hover:text-slate-700',
          )}
          disabled={isPending}
          onClick={() => onModeChange('LLM')}
          type="button"
        >
          LLM 직접 분석
        </button>
      </div>
    </fieldset>

    <fieldset
      className={cn(
        'ml-auto flex items-center gap-3 pl-4 transition-opacity',
        mode !== 'LLM' && 'opacity-40',
      )}
      title={mode === 'LLM' ? undefined : 'LLM 직접 분석에서 사용할 수 있어요.'}
    >
      <legend className="sr-only">분석 깊이</legend>
      <div className="shrink-0">
        <p className="text-xs font-extrabold text-slate-500">분석 깊이</p>
      </div>
      <div className="inline-flex items-center rounded-xl bg-white p-1 shadow-sm ring-1 ring-slate-100">
        {DEPTH_OPTIONS.map(([value, label]) => (
          <button
            aria-pressed={mode === 'LLM' && depth === value}
            className={cn(
              'rounded-lg px-3 py-2 text-xs font-bold transition',
              mode === 'LLM' && depth === value
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-500 hover:text-slate-700',
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
    </fieldset>
  </div>
)

export default AnalysisOptions
