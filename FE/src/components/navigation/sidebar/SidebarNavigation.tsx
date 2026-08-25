import {
  Building2,
  FileSpreadsheet,
  LayoutDashboard,
  Newspaper,
  UserRoundSearch,
  UsersRound,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
  ROUTES,
} from '@/constants/navigation'
import { cn } from '@/utils/cn'

interface SidebarNavigationProps {
  onNavigate: () => void
}

const NAVIGATION_ICONS = {
  'public-monitor': Building2,
  'person-news': UserRoundSearch,
  'news-collection': Newspaper,
  'excel-analysis': FileSpreadsheet,
} as const

const navigationClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    'sidebar-nav-item',
    isActive
      ? 'sidebar-nav-item-active'
      : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
  )

const SidebarNavigation = ({ onNavigate }: SidebarNavigationProps) => {
  const { user } = useAuth()

  return (
    <nav
      aria-label="주요 메뉴"
      className="sidebar-navigation min-h-0 flex-1 overflow-y-auto px-3 py-5"
    >
      <NavLink
        className={navigationClassName}
        end
        onClick={onNavigate}
        to={DASHBOARD_NAVIGATION_ITEM.to}
      >
        <LayoutDashboard aria-hidden="true" size={19} strokeWidth={1.9} />
        <span>{DASHBOARD_NAVIGATION_ITEM.label}</span>
      </NavLink>

      <NavigationLabel>업무</NavigationLabel>
      <div className="space-y-1.5">
        {BUSINESS_NAVIGATION_ITEMS.map((item) => {
          const Icon = NAVIGATION_ICONS[item.id]
          return (
            <NavLink
              className={({ isActive }) =>
                cn('business-navigation-item', navigationClassName({ isActive }))
              }
              key={item.id}
              onClick={onNavigate}
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
          <NavigationLabel>관리</NavigationLabel>
          <NavLink
            className={navigationClassName}
            onClick={onNavigate}
            to={ROUTES.userManagement}
          >
            <UsersRound aria-hidden="true" size={19} strokeWidth={1.9} />
            <span>사용자 관리</span>
          </NavLink>
        </>
      )}
    </nav>
  )
}

const NavigationLabel = ({ children }: { children: string }) => (
  <p className="mb-2 mt-7 px-3 text-[0.67rem] font-bold tracking-[0.12em] text-slate-400">
    {children}
  </p>
)

export default SidebarNavigation
