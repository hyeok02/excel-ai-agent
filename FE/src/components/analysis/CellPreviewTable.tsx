import type { CellResult } from '@/api/analysis'

interface CellPreviewTableProps {
  rows: CellResult[][]
}

const formatCellValue = (cell: CellResult) => {
  if (cell.formula) return cell.formula
  if (cell.value === null || cell.value === '') return '—'
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
                  className="min-w-32 max-w-64 border-r border-slate-100 p-3 align-top last:border-r-0"
                  key={cell.address}
                  title={formatCellValue(cell)}
                >
                  <span className="block text-[10px] font-bold text-slate-400">
                    {cell.address}
                  </span>
                  <code
                    className={`mt-1 block truncate font-sans leading-5 ${
                      cell.formula ? 'font-semibold text-brand-700' : 'text-slate-700'
                    }`}
                  >
                    {formatCellValue(cell)}
                  </code>
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
