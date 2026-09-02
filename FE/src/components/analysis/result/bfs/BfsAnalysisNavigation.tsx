import { Braces, Network, ShieldAlert, Table2 } from 'lucide-react'

import { cn } from '@/utils/cn'

export type BfsView = 'flow' | 'risk' | 'structure' | 'source'

interface BfsAnalysisNavigationProps {
  activeView: BfsView
  clusterCount: number
  onChange: (view: BfsView) => void
  riskCount: number
  sheetCount: number
}

const BfsAnalysisNavigation = ({
  activeView,
  clusterCount,
  onChange,
  riskCount,
  sheetCount,
}: BfsAnalysisNavigationProps) => {
  const tabs = [
    {
      id: 'flow',
      label: '계산 구조',
      description: `${clusterCount.toLocaleString()}개 계산 흐름`,
      icon: Network,
    },
    {
      id: 'risk',
      label: '수식 점검',
      description: `${riskCount.toLocaleString()}건 확인`,
      icon: ShieldAlert,
    },
    {
      id: 'structure',
      label: '워크북 구조',
      description: `${sheetCount.toLocaleString()}개 시트 역할`,
      icon: Braces,
    },
    {
      id: 'source',
      label: '원본 시트',
      description: '셀과 데이터 확인',
      icon: Table2,
    },
  ] as const

  return (
    <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 p-5 md:p-6">
        <div>
          <div className="flex items-center gap-2 text-brand-700">
            <Network aria-hidden="true" size={17} />
            <span className="text-xs font-extrabold tracking-[0.12em]">
              BFS 수식 관계 분석
            </span>
          </div>
          <h3 className="mt-2 text-lg font-extrabold text-slate-950">
            계산 흐름부터 필요한 항목만 확인하세요
          </h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            결과를 네 영역으로 나눴습니다. 한 번에 하나만 열어 복잡한 워크북도 빠르게
            검토할 수 있습니다.
          </p>
        </div>
      </header>

      <div
        aria-label="BFS 분석 결과 선택"
        className="grid gap-2 bg-slate-50 p-2 sm:grid-cols-2 xl:grid-cols-4"
        role="tablist"
      >
        {tabs.map(({ id, label, description, icon: Icon }) => {
          const selected = activeView === id
          return (
            <button
              aria-controls={`bfs-panel-${id}`}
              aria-selected={selected}
              className={cn(
                'flex items-center gap-3 rounded-2xl px-4 py-3 text-left transition',
                selected
                  ? 'bg-white text-brand-700 shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-500 hover:bg-white/70 hover:text-slate-700',
              )}
              key={id}
              onClick={() => onChange(id)}
              role="tab"
              type="button"
            >
              <span
                className={cn(
                  'grid size-9 shrink-0 place-items-center rounded-xl',
                  selected ? 'bg-brand-50' : 'bg-white',
                )}
              >
                <Icon aria-hidden="true" size={17} />
              </span>
              <span>
                <span className="block text-sm font-extrabold">{label}</span>
                <span className="mt-0.5 block text-[11px] font-semibold text-slate-400">
                  {description}
                </span>
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default BfsAnalysisNavigation
