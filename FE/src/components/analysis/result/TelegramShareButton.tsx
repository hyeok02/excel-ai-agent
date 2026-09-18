import { Send } from 'lucide-react'
import { useState } from 'react'

import TelegramShareDialog from '@/components/analysis/result/TelegramShareDialog'

interface TelegramShareButtonProps {
  analysisId: string
}

const TelegramShareButton = ({ analysisId }: TelegramShareButtonProps) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        className="inline-flex h-10 min-w-24 items-center justify-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50 px-3 text-xs font-extrabold text-sky-700 shadow-sm transition hover:border-sky-300 hover:bg-sky-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
        onClick={() => setIsOpen(true)}
        title="분석 결과를 텔레그램 수신자에게 보냅니다."
        type="button"
      >
        <Send aria-hidden="true" size={15} />
        텔레그램
      </button>
      {isOpen && (
        <TelegramShareDialog analysisId={analysisId} onClose={() => setIsOpen(false)} />
      )}
    </>
  )
}

export default TelegramShareButton
