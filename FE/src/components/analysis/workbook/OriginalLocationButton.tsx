import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

interface OriginalLocationButtonProps {
  sheetName: string
  location: string
}

const excelLocation = (sheetName: string, location: string) => {
  const escapedSheetName = sheetName.replaceAll("'", "''")
  return `'${escapedSheetName}'!${location}`
}

const OriginalLocationButton = ({ sheetName, location }: OriginalLocationButtonProps) => {
  const [copied, setCopied] = useState(false)
  const target = excelLocation(sheetName, location)

  const copyLocation = async () => {
    await navigator.clipboard.writeText(target)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <button
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-bold text-slate-500 transition hover:border-brand-200 hover:text-brand-700"
      onClick={copyLocation}
      title={`${target} 위치를 복사합니다`}
      type="button"
    >
      {copied ? <Check aria-hidden="true" size={12} /> : <Copy aria-hidden="true" size={12} />}
      {copied ? '위치 복사됨' : '원본 위치 복사'}
    </button>
  )
}

export default OriginalLocationButton
