import {
  Building2,
  FileSpreadsheet,
  LayoutDashboard,
  Newspaper,
  Sparkles,
  UserRoundSearch,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import {
  BUSINESS_NAVIGATION_ITEMS,
  DASHBOARD_NAVIGATION_ITEM,
} from '@/constants/navigation'
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
          'fixed inset-y-0 left-0 z-40 flex w-[15.5rem] flex-col overflow-y-auto border-r border-slate-200/80 bg-white transition-transform duration-200 lg:sticky lg:top-0 lg:h-dvh lg:translate-x-0',
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
                Yun's AI WORKSPACE
              </p>
            </div>
          </div>
        </div>

        <nav className="sidebar-navigation flex-1 px-3 py-5" aria-label="주요 메뉴">
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
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
