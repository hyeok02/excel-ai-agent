interface ReferenceRun {
  column: string
  endRow: number
  length: number
  startRow: number
}

const findLongestReferenceRun = (formula: string): ReferenceRun | null => {
  const references = [...formula.matchAll(/\$?([A-Z]{1,3})\$?(\d+)/gi)].map(
    ([, column, row]) => ({ column: column.toUpperCase(), row: Number(row) }),
  )
  let best: ReferenceRun | null = null
  let currentColumn = ''
  let currentEndRow = 0
  let currentLength = 0
  let currentStartRow = 0

  for (const { column, row } of references) {
    if (currentColumn === column && row === currentEndRow + 1) {
      currentEndRow = row
      currentLength += 1
    } else {
      currentColumn = column
      currentEndRow = row
      currentLength = 1
      currentStartRow = row
    }
    if (!best || currentLength > best.length) {
      best = {
        column: currentColumn,
        endRow: currentEndRow,
        length: currentLength,
        startRow: currentStartRow,
      }
    }
  }

  return best && best.length >= 3 ? best : null
}

const findSumRange = (formula: string) => {
  const match = formula.match(
    /SUM\s*\(\s*\$?([A-Z]{1,3})\$?(\d+)\s*:\s*\$?([A-Z]{1,3})\$?(\d+)\s*\)/i,
  )
  if (!match) return null
  return `${match[1].toUpperCase()}${match[2]}:${match[3].toUpperCase()}${match[4]}`
}

const CONCATENATED_REFERENCES =
  /(?:\$?[A-Z]{1,3}\$?\d+\s*&\s*){2,}\$?[A-Z]{1,3}\$?\d+/gi

const compactReferenceChain = (chain: string): string | null => {
  const references = [...chain.matchAll(/\$?([A-Z]{1,3})\$?(\d+)/gi)].map(
    ([, column, row]) => ({ column: column.toUpperCase(), row: Number(row) }),
  )
  if (references.length < 3) return null

  const [first] = references
  const isContiguous = references.every(
    ({ column, row }, index) => column === first.column && row === first.row + index,
  )
  if (!isContiguous) return null

  const last = references.at(-1)
  return `TEXTJOIN("",TRUE,${first.column}${first.row}:${last?.column}${last?.row})`
}

export const compactFormula = (formula: string): string | null => {
  let compacted = formula
  let changed = false

  compacted = compacted.replace(CONCATENATED_REFERENCES, (chain) => {
    const replacement = compactReferenceChain(chain)
    if (!replacement) return chain
    changed = true
    return replacement
  })

  return changed ? compacted : null
}

export const summarizeFormula = (formula: string): string | null => {
  const run = findLongestReferenceRun(formula)
  if (!run || !formula.includes('&')) return null

  const connectedRange = `${run.column}${run.startRow}:${run.column}${run.endRow}`
  const sumRange = findSumRange(formula)
  const hasBlankFallback = /=\s*0\s*,\s*""/.test(formula)

  if (/\bIF\s*\(/i.test(formula) && sumRange && hasBlankFallback) {
    return `${sumRange} 합계가 0이면 빈값을 표시하고, 아니면 ${connectedRange}의 텍스트를 순서대로 연결합니다.`
  }
  return `${connectedRange}의 텍스트를 순서대로 연결해 결과를 만듭니다.`
}
