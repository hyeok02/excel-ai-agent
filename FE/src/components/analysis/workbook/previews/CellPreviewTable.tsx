import type { CellResult } from '@/api/analysis'
import { SemanticRoleBadge } from '@/components/analysis/workbook/semantic/components/ClassificationBadges'

interface CellPreviewTableProps {
  rows: CellResult[][]
}

const formatCellValue = (cell: CellResult) => {
  if (cell.formula && cell.cachedValue != null && cell.cachedValue !== '') {
    return String(cell.cachedValue)
  }
  if (cell.formula) return '수식 셀'
  if (cell.value == null || cell.value === '') return '빈 셀'
  if (typeof cell.value === 'boolean') return cell.value ? 'TRUE' : 'FALSE'
  return String(cell.value)
}

const CellPreviewTable = ({ rows }: CellPreviewTableProps) => {
  if (rows.length === 0) {
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
          {rows.map((row, rowIndex) => (
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
                  <span className="mt-1 flex flex-wrap gap-1 text-[9px] font-bold text-slate-400">
                    {cell.semantic && (
                      <SemanticRoleBadge compact role={cell.semantic.role} />
                    )}
                    {cell.formula && !cell.semantic && (
                      <span className="text-brand-600">수식</span>
                    )}
                    {cell.formula && cell.cachedValue != null && (
                      <span>계산 결과 표시</span>
                    )}
                    {cell.merged && <span>병합</span>}
                    {cell.numberFormat && cell.numberFormat !== 'General' && (
                      <span>{cell.numberFormat}</span>
                    )}
                  </span>
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
