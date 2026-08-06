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
          'fixed inset-y-0 left-0 z-40 flex w-[18.5rem] flex-col overflow-y-auto border-r border-slate-200 bg-white transition-transform duration-200 lg:sticky lg:top-6 lg:ml-6 lg:h-[calc(100dvh-3rem)] lg:translate-x-0 lg:rounded-[1.75rem] lg:border lg:shadow-panel',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="sidebar-brand-block px-7 pb-6 pt-8">
          <p className="text-lg font-black tracking-tight">
            <span className="text-[#e11d2e]">SK</span>{' '}
            <span className="text-[#f59e0b]">hynix</span>
          </p>
          <p className="mt-4 text-[1.7rem] font-black leading-[1.05] tracking-[-0.04em] text-slate-950">
            Decision Support
            <br />
            System
          </p>
          <p className="system-description mt-4 text-sm leading-6 text-slate-500">
            POC screens and tool servers are separated by menu so the next expansion step
            stays manageable.
          </p>
        </div>

        <div className="operator-card mx-7 rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-500">Signed in as</p>
          <p className="mt-4 text-xl font-bold text-slate-950">Line Operator</p>
          <p className="mt-1 text-sm text-slate-500">operations-admin</p>
        </div>

        <nav className="sidebar-navigation flex-1 px-5 py-7" aria-label="주요 메뉴">
          <NavLink
            className={({ isActive }) =>
              cn(
                'block rounded-xl px-4 py-3 text-sm font-semibold transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-700 hover:bg-slate-50',
              )
            }
            end
            onClick={onClose}
            to={DASHBOARD_NAVIGATION_ITEM.to}
          >
            {DASHBOARD_NAVIGATION_ITEM.label}
          </NavLink>

          <div className="mt-6 px-4">
            <p className="text-sm font-bold text-slate-800">업무</p>
          </div>

          <div className="mt-3 space-y-1">
            {BUSINESS_NAVIGATION_ITEMS.map((item) => (
              <NavLink
                className={({ isActive }) =>
                  cn(
                    'business-navigation-item flex items-center justify-between rounded-xl px-4 py-3 text-sm font-semibold transition-colors',
                    isActive
                      ? 'bg-brand-50 text-sky-600'
                      : 'text-slate-700 hover:bg-slate-50',
                  )
                }
                key={item.id}
                onClick={onClose}
                to={item.to}
              >
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      </aside>
    </>
  )
}

export default Sidebar
