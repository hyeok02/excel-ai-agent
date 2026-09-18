import { Menu } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import BistelligenceLogo from '@/components/navigation/brand/BistelligenceLogo'
import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
  PENDING_NAVIGATION_ITEMS,
  ROUTES,
} from '@/constants/navigation'

interface AppHeaderProps {
  onMenuClick: () => void
}

const MANAGEMENT_HEADER_ITEMS = [
  { to: ROUTES.userManagement, label: '사용자 관리' },
  { to: ROUTES.telegramRecipients, label: '텔레그램 수신자' },
] as const

const AppHeader = ({ onMenuClick }: AppHeaderProps) => {
  const { pathname } = useLocation()
  // 노출하지 않는 모듈도 주소로 직접 들어올 수 있어, 제목은 양쪽에서 찾는다.
  const currentItem = [
    ...BUSINESS_NAVIGATION_ITEMS,
    ...PENDING_NAVIGATION_ITEMS,
    ...MANAGEMENT_HEADER_ITEMS,
  ].find((item) => pathname.startsWith(item.to))
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
          <Menu aria-hidden="true" size={19} />
        </button>
        <div>
          <p className="text-[0.68rem] font-bold tracking-[0.12em] text-slate-400">
            DECISION SUPPORT
          </p>
          <p className="mt-0.5 text-sm font-bold text-slate-900">{currentLabel}</p>
        </div>
      </div>

      <div className="w-[9.25rem] max-w-[42vw]">
        <BistelligenceLogo />
      </div>
    </header>
  )
}

export default AppHeader
