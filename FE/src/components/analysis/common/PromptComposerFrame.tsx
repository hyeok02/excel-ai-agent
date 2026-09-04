import type { ReactNode } from 'react'

interface PromptComposerFrameProps {
  action: ReactNode
  children: ReactNode
  hint: ReactNode
}

export const promptComposerTextareaClassName =
  'w-full bg-transparent px-3 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400'

export const promptComposerActionClassName =
  'ml-auto inline-flex h-9 items-center gap-2 rounded-xl bg-brand-600 px-4 text-xs font-extrabold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300'

const PromptComposerFrame = ({ action, children, hint }: PromptComposerFrameProps) => (
  <div className="rounded-2xl border border-brand-200 bg-white p-2 shadow-sm transition focus-within:ring-2 focus-within:ring-brand-100">
    {children}
    <div className="flex items-center justify-between gap-3 border-t border-slate-100 px-2 pt-2">
      <span className="hidden items-center gap-1 text-[11px] text-slate-400 sm:flex">
        {hint}
      </span>
      {action}
    </div>
  </div>
)

export default PromptComposerFrame
