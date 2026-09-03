import type { WritebackStatus } from '@/api/analysis'
import { WRITEBACK_STATUS_PRESENTATION } from '@/components/analysis/result/writeback/writebackPresentation'

const WritebackStatusBadge = ({ status }: { status: WritebackStatus }) => {
  const presentation = WRITEBACK_STATUS_PRESENTATION[status]
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-extrabold ${presentation.style}`}
    >
      {presentation.label}
    </span>
  )
}

export default WritebackStatusBadge
