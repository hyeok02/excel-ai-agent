import { LoaderCircle, LogOut } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/auth-context'
import { ROUTES } from '@/constants/navigation'

interface SidebarAccountPanelProps {
  onLogout: () => void
}

const SidebarAccountPanel = ({ onLogout }: SidebarAccountPanelProps) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logout()
      onLogout()
      navigate(ROUTES.login, { replace: true })
    } finally {
      setIsLoggingOut(false)
    }
  }

  return (
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
  )
}

export default SidebarAccountPanel
