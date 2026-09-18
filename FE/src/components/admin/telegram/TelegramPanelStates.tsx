import { LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'

export const TelegramLoadingState = ({ label }: { label: string }) => (
  <div className="flex min-h-56 items-center justify-center gap-2 text-sm font-medium text-slate-400">
    <LoaderCircle className="animate-spin text-brand-500" size={18} /> {label}
  </div>
)

export const TelegramEmptyState = ({
  description,
  icon,
  title,
}: {
  description: string
  icon: ReactNode
  title: string
}) => (
  <div className="m-5 flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-6 text-center">
    <span className="grid size-12 place-items-center rounded-2xl bg-white text-brand-600 shadow-sm">
      {icon}
    </span>
    <p className="mt-4 text-sm font-extrabold text-slate-800">{title}</p>
    <p className="mt-1 max-w-xs text-xs leading-5 text-slate-400">{description}</p>
  </div>
)
