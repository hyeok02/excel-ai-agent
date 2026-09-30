import { Mail } from 'lucide-react'
import { useState } from 'react'

import EmailShareDialog from '@/components/analysis/result/EmailShareDialog'

interface EmailShareButtonProps {
  analysisId: string
}

const EmailShareButton = ({ analysisId }: EmailShareButtonProps) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        className="inline-flex h-10 min-w-24 items-center justify-center gap-1.5 rounded-xl border border-brand-200 bg-brand-50 px-3 text-xs font-extrabold text-brand-700 shadow-sm transition hover:border-brand-300 hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        onClick={() => setIsOpen(true)}
        title="분석 결과를 이메일 수신자에게 보냅니다."
        type="button"
      >
        <Mail aria-hidden="true" size={15} />
        이메일
      </button>
      {isOpen && (
        <EmailShareDialog analysisId={analysisId} onClose={() => setIsOpen(false)} />
      )}
    </>
  )
}

export default EmailShareButton
