import { Sparkles } from 'lucide-react'

import SidebarAccountPanel from '@/components/navigation/sidebar/SidebarAccountPanel'
import SidebarNavigation from '@/components/navigation/sidebar/SidebarNavigation'
import { cn } from '@/utils/cn'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

const Sidebar = ({ isOpen, onClose }: SidebarProps) => (
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

      <SidebarNavigation onNavigate={onClose} />
      <SidebarAccountPanel onLogout={onClose} />
    </aside>
  </>
)

export default Sidebar
