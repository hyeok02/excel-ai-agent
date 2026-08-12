import { useLocation } from 'react-router-dom'

import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
} from '@/constants/navigation'

interface AppHeaderProps {
  onMenuClick: () => void
}

const AppHeader = ({ onMenuClick }: AppHeaderProps) => {
  const { pathname } = useLocation()
  const currentItem = BUSINESS_NAVIGATION_ITEMS.find((item) =>
    pathname.startsWith(item.to),
  )
  const currentLabel = currentItem?.label ?? DASHBOARD_NAVIGATION_ITEM.label

  return (
    <header className="sticky top-0 z-20 flex h-[4.5rem] items-center justify-between border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-xl md:px-8">
      <div className="flex items-center gap-3">
        <button
          aria-label="메뉴 열기" 
          className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-lg text-slate-700 shadow-sm lg:hidden"
          onClick={onMenuClick}
          type="button"
        >
          ☰
        </button>
        <div>
          <p className="text-[0.68rem] font-bold tracking-[0.12em] text-slate-400">
            DECISION SUPPORT
          </p>
          <p className="mt-0.5 text-sm font-bold text-slate-900">{currentLabel}</p>
        </div>
      </div>

      <div aria-label="현재 사용자" className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-xs font-bold text-slate-700">Yun</p>
          <p className="mt-0.5 text-[0.67rem] font-medium text-slate-400">
            AI Agent Developer
          </p>
        </div>
        <div className="grid size-9 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white shadow-sm">
          Y
        </div>
      </div>
    </header>
  )
}

export default AppHeader
