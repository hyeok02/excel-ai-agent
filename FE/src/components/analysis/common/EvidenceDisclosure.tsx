import { ChevronDown, FileSpreadsheet } from 'lucide-react'
import type { ReactNode } from 'react'

interface EvidenceDisclosureProps {
  ariaLabel: string
  children: ReactNode
  count: number
}

/** 인사이트 카드와 질문 답변이 같은 모양의 '원본 근거' 펼침 영역을 쓰도록 모아 둔다. */
const EvidenceDisclosure = ({ ariaLabel, children, count }: EvidenceDisclosureProps) => (
  <details className="group mt-4 border-t border-slate-200 pt-3">
    <summary
      aria-label={ariaLabel}
      className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-md text-xs font-semibold text-slate-500 transition hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
    >
      <FileSpreadsheet aria-hidden="true" size={14} />
      원본 근거 <span aria-hidden="true">· {count}개</span>
      <ChevronDown
        aria-hidden="true"
        className="transition-transform group-open:rotate-180"
        size={13}
      />
    </summary>
    <div className="mt-3">{children}</div>
  </details>
)

export default EvidenceDisclosure
