import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import AppHeader from '@/components/navigation/AppHeader'
import Sidebar from '@/components/navigation/Sidebar'

const RootLayout = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="min-h-dvh bg-app-background text-slate-900 lg:flex">
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      <div className="min-w-0 flex-1">
        <AppHeader onMenuClick={() => setIsSidebarOpen(true)} />
        <main className="page-container">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default RootLayout
