import type { CellResult } from '@/api/analysis'
import { SemanticRoleBadge } from '@/components/analysis/workbook/semantic/components/ClassificationBadges'

interface CellPreviewTableProps {
  compact?: boolean
  rows: CellResult[][]
}

const formatCellValue = (cell: CellResult) => {
  if (cell.formula && cell.cachedValue != null && cell.cachedValue !== '') {
    return String(cell.cachedValue)
  }
  if (cell.formula) return '수식 셀'
  if (cell.value == null || cell.value === '') return ''
  if (typeof cell.value === 'boolean') return cell.value ? 'TRUE' : 'FALSE'
  return String(cell.value)
}

const CellPreviewTable = ({ compact = false, rows }: CellPreviewTableProps) => {
  const visibleRows = rows
    .map((row) =>
      row.filter(
        (cell) =>
          cell.formula || (cell.value != null && String(cell.value).trim() !== ''),
      ),
    )
    .filter((row) => row.length > 0)

  if (visibleRows.length === 0) {
    return (
      <p className="rounded-xl bg-slate-50 p-4 text-xs text-slate-400">
        표시할 셀 미리보기가 없습니다.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="min-w-full border-collapse text-left text-xs">
        <tbody>
          {visibleRows.map((row, rowIndex) => (
            <tr className="border-b border-slate-100 last:border-0" key={rowIndex}>
              {row.map((cell) => (
                <td
                  className={`min-w-32 max-w-64 border-r border-slate-100 p-3 align-top last:border-r-0 ${
                    cell.merged ? 'bg-brand-50/40' : ''
                  }`}
                  key={cell.address}
                  title={formatCellValue(cell)}
                >
                  <span className="block text-[10px] font-bold text-slate-400">
                    {cell.address}
                  </span>
                  <code
                    className={`mt-1 block truncate font-sans leading-5 ${cell.bold ? 'font-extrabold' : 'font-medium'} text-slate-700`}
                  >
                    {formatCellValue(cell)}
                  </code>
                  {(!compact || cell.formula) && (
                    <span className="mt-1 flex flex-wrap gap-1 text-[9px] font-bold text-slate-400">
                      {!compact && cell.semantic && (
                        <SemanticRoleBadge compact role={cell.semantic.role} />
                      )}
                      {cell.formula && (compact || !cell.semantic) && (
                        <span className="text-brand-600">수식</span>
                      )}
                      {!compact && cell.formula && cell.cachedValue != null && (
                        <span>계산 결과 표시</span>
                      )}
                      {!compact && cell.merged && <span>병합</span>}
                      {!compact &&
                        cell.numberFormat &&
                        cell.numberFormat !== 'General' && (
                          <span>{cell.numberFormat}</span>
                        )}
                    </span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default CellPreviewTable
