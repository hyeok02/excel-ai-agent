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
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden">
      <div className="flex items-center gap-3">
        <button
          aria-label="메뉴 열기"
          className="grid size-10 place-items-center rounded-lg border border-slate-200 text-lg text-slate-700 lg:hidden"
          onClick={onMenuClick}
          type="button"
        >
          ☰
        </button>
        <div>
          <p className="text-sm font-semibold text-slate-950">{currentLabel}</p>
          <p className="text-xs text-slate-500">Decision Support System</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="grid size-9 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">
          OP
        </div>
      </div>
    </header>
  )
}

export default AppHeader
