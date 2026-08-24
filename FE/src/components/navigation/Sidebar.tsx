import {
  Building2,
  FileSpreadsheet,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Newspaper,
  Sparkles,
  UserRoundSearch,
  UsersRound,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
} from '@/constants/navigation'
import { ROUTES } from '@/constants/navigation'
import { cn } from '@/utils/cn'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

const NAVIGATION_ICONS = {
  'public-monitor': Building2,
  'person-news': UserRoundSearch,
  'news-collection': Newspaper,
  'excel-analysis': FileSpreadsheet,
} as const

const Sidebar = ({ isOpen, onClose }: SidebarProps) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      onClose()
      navigate(ROUTES.login, { replace: true })
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
    <>
      <button
        aria-label="사이드바 닫기"
        className={cn(
          'fixed inset-0 z-30 bg-slate-950/30 backdrop-blur-[1px] transition-opacity lg:hidden',
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={onClose}
        type="button"
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[15.5rem] flex-col overflow-hidden border-r border-slate-200/80 bg-white transition-transform duration-200 lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="sidebar-brand-block px-5 pb-4 pt-6">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-xl bg-brand-600 text-white shadow-brand">
              <Sparkles aria-hidden="true" size={18} strokeWidth={2.2} />
            </span>
            <div>
              <p className="text-[0.95rem] font-extrabold tracking-[-0.025em] text-slate-950">
                Decision Support
              </p>
              <p className="mt-0.5 text-[0.65rem] font-semibold tracking-[0.1em] text-slate-400">
                AI WORKSPACE
              </p>
            </div>
          </div>
        </div>

        <nav
          className="sidebar-navigation min-h-0 flex-1 overflow-y-auto px-3 py-5"
          aria-label="주요 메뉴"
        >
          <NavLink
            className={({ isActive }) =>
              cn(
                'sidebar-nav-item',
                isActive
                  ? 'sidebar-nav-item-active'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
              )
            }
            end
            onClick={onClose}
            to={DASHBOARD_NAVIGATION_ITEM.to}
          >
            <LayoutDashboard aria-hidden="true" size={19} strokeWidth={1.9} />
            <span>{DASHBOARD_NAVIGATION_ITEM.label}</span>
          </NavLink>

          <p className="mb-2 mt-7 px-3 text-[0.67rem] font-bold tracking-[0.12em] text-slate-400">
            업무
          </p>

          <div className="space-y-1.5">
            {BUSINESS_NAVIGATION_ITEMS.map((item) => {
              const Icon = NAVIGATION_ICONS[item.id]
              return (
                <NavLink
                  className={({ isActive }) =>
                    cn(
                      'business-navigation-item sidebar-nav-item',
                      isActive
                        ? 'sidebar-nav-item-active'
                        : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
                    )
                  }
                  key={item.id}
                  onClick={onClose}
                  to={item.to}
                >
                  <Icon aria-hidden="true" size={19} strokeWidth={1.9} />
                  <span>{item.label}</span>
                </NavLink>
              )
            })}
          </div>

          {user?.role === 'ADMIN' && (
            <>
              <p className="mb-2 mt-7 px-3 text-[0.67rem] font-bold tracking-[0.12em] text-slate-400">
                관리
              </p>
              <NavLink
                className={({ isActive }) =>
                  cn(
                    'sidebar-nav-item',
                    isActive
                      ? 'sidebar-nav-item-active'
                      : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
                  )
                }
                onClick={onClose}
                to={ROUTES.userManagement}
              >
                <UsersRound aria-hidden="true" size={19} strokeWidth={1.9} />
                <span>사용자 관리</span>
              </NavLink>
            </>
          )}
        </nav>

        <div className="shrink-0 border-t border-slate-100 bg-white p-3">
          <div className="rounded-2xl border border-slate-200/80 bg-gradient-to-br from-slate-50 to-white p-2 shadow-[0_10px_30px_rgb(15_23_42/5%)]">
            <div className="flex items-center gap-2.5 px-2 py-2">
              <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-[0.7rem] font-extrabold text-white shadow-sm">
                {user?.displayName.slice(0, 1).toUpperCase()}
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-bold text-slate-800">
                  {user?.displayName}
                </p>
                <p className="mt-0.5 truncate text-[0.65rem] font-medium text-slate-400">
                  {user?.role === 'ADMIN' ? 'System Administrator' : 'Workspace User'}
                </p>
              </div>
            </div>

            <button
              className="group mt-1 flex h-10 w-full items-center justify-between rounded-xl border border-slate-200/80 bg-white px-3 text-xs font-bold text-slate-600 shadow-sm transition hover:border-red-100 hover:bg-red-50 hover:text-red-600 disabled:cursor-wait disabled:opacity-60"
              disabled={isLoggingOut}
              onClick={() => void handleLogout()}
              type="button"
            >
              <span>로그아웃</span>
              {isLoggingOut ? (
                <LoaderCircle className="animate-spin" size={16} />
              ) : (
                <span className="grid size-6 place-items-center rounded-lg bg-slate-100 text-slate-500 transition group-hover:bg-white group-hover:text-red-500">
                  <LogOut aria-hidden="true" size={14} strokeWidth={2} />
                </span>
              )}
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
