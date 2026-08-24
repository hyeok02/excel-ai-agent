import { LogOut, Menu, UserRound } from 'lucide-react'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
} from '@/constants/navigation'
import { ROUTES } from '@/constants/navigation'

interface AppHeaderProps {
  onMenuClick: () => void
}

const AppHeader = ({ onMenuClick }: AppHeaderProps) => {
  const { pathname } = useLocation()
  const currentItem = BUSINESS_NAVIGATION_ITEMS.find((item) =>
    pathname.startsWith(item.to),
  )
  const currentLabel = currentItem?.label ?? DASHBOARD_NAVIGATION_ITEM.label
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate(ROUTES.login, { replace: true })
  }

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

      <div aria-label="현재 사용자" className="relative">
        <button
          aria-expanded={isUserMenuOpen}
          className="flex items-center gap-3 rounded-xl px-2 py-1.5 transition hover:bg-slate-50"
          onClick={() => setIsUserMenuOpen((open) => !open)}
          type="button"
        >
          <div className="hidden text-right sm:block">
            <p className="text-xs font-bold text-slate-700">{user?.displayName}</p>
            <p className="mt-0.5 text-[0.67rem] font-medium text-slate-400">
              {user?.role === 'ADMIN' ? 'System Administrator' : 'Workspace User'}
            </p>
          </div>
          <div className="grid size-9 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white shadow-sm">
            {user?.displayName.slice(0, 1).toUpperCase()}
          </div>
        </button>

        {isUserMenuOpen && (
          <div className="absolute right-0 top-[3.2rem] z-40 w-56 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
            <div className="flex items-center gap-3 border-b border-slate-100 px-3 py-3">
              <span className="grid size-9 place-items-center rounded-xl bg-brand-50 text-brand-600">
                <UserRound size={17} />
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-bold text-slate-900">
                  {user?.displayName}
                </p>
                <p className="mt-0.5 truncate text-[0.68rem] text-slate-400">
                  {user?.email ?? user?.username}
                </p>
              </div>
            </div>
            <button
              className="mt-1 flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
              onClick={() => void handleLogout()}
              type="button"
            >
              <LogOut size={16} /> 로그아웃
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

export default AppHeader
