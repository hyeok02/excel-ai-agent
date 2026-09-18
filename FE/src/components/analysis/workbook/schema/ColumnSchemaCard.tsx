import { ArrowRight, Braces } from 'lucide-react'

import type { ColumnSchemaResult } from '@/api/analysis'
import OriginalLocationButton from '@/components/analysis/workbook/details/OriginalLocationButton'
import {
  DATA_TYPE_LABELS,
  labelFor,
  STANDARD_FIELD_LABELS,
  UNIT_TYPE_LABELS,
} from '@/components/analysis/workbook/schema/schemaPresentation'

interface ColumnSchemaCardProps {
  column: ColumnSchemaResult
  sheetName: string
}

const ColumnSchemaCard = ({ column, sheetName }: ColumnSchemaCardProps) => {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm shadow-slate-100/70">
      <p className="text-[10px] font-extrabold text-brand-600">열 {column.column}</p>

      <div className="mt-2 flex min-w-0 items-center gap-2">
        <p
          className="truncate text-xs font-extrabold text-slate-800"
          title={column.displayName}
        >
          {column.displayName}
        </p>
        <ArrowRight aria-hidden="true" className="shrink-0 text-slate-300" size={13} />
        <p className="shrink-0 text-xs font-extrabold text-indigo-700">
          {labelFor(STANDARD_FIELD_LABELS, column.standardField)}
        </p>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] font-semibold">
        <span className="rounded-md bg-slate-50 px-2 py-1 text-slate-600">
          {labelFor(DATA_TYPE_LABELS, column.dataType)}
        </span>
        <span className="rounded-md bg-cyan-50 px-2 py-1 text-cyan-700">
          {labelFor(UNIT_TYPE_LABELS, column.unitType)}
          {column.unitLabel ? ` · ${column.unitLabel}` : ''}
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2.5">
        <p className="flex min-w-0 items-center gap-1 truncate text-[10px] text-slate-400">
          <Braces aria-hidden="true" size={11} />
          {column.standardField}
        </p>
        <OriginalLocationButton location={column.sourceRange} sheetName={sheetName} />
      </div>
    </article>
  )
}

export default ColumnSchemaCard
