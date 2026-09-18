import { CheckCircle2, Ruler, TableColumnsSplit } from 'lucide-react'

interface ColumnSchemaSummaryProps {
  classifiedCount: number
  totalCount: number
  unitCount: number
}

const items = [
  { key: 'total', label: '전체 열', icon: TableColumnsSplit, tone: 'text-indigo-600' },
  { key: 'classified', label: '의미 분류', icon: CheckCircle2, tone: 'text-emerald-600' },
  { key: 'unit', label: '단위 인식', icon: Ruler, tone: 'text-cyan-600' },
] as const

const ColumnSchemaSummary = ({
  classifiedCount,
  totalCount,
  unitCount,
}: ColumnSchemaSummaryProps) => {
  const counts = {
    classified: classifiedCount,
    total: totalCount,
    unit: unitCount,
  }

  return (
    <div className="mt-4 grid grid-cols-3 gap-2">
      {items.map(({ icon: Icon, key, label, tone }) => (
        <div
          className="rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-2.5"
          key={key}
        >
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500">
            <Icon aria-hidden="true" className={tone} size={13} />
            {label}
          </div>
          <p className="mt-1 text-base font-black text-slate-900">{counts[key]}</p>
        </div>
      ))}
    </div>
  )
}

export default ColumnSchemaSummary
