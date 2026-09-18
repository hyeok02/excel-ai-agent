import type { ColumnSchemaResult } from '@/api/analysis'

export type ColumnSchemaView = 'important' | 'all'

export const isClassifiedColumn = (column: ColumnSchemaResult) =>
  column.standardField !== 'unknown'

export const hasDetectedUnit = (column: ColumnSchemaResult) => column.unitType !== 'none'

/** 의미가 판정된 열, 그중에서도 단위까지 읽어낸 열을 앞으로 보낸다. */
export const prioritizeColumns = (columns: ColumnSchemaResult[]) =>
  [...columns].sort((left, right) => {
    const score = (column: ColumnSchemaResult) =>
      Number(isClassifiedColumn(column)) * 2 + Number(hasDetectedUnit(column))
    return score(right) - score(left)
  })

export const columnsForView = (columns: ColumnSchemaResult[], view: ColumnSchemaView) => {
  if (view === 'all') return columns

  const seenMeanings = new Set<string>()
  return prioritizeColumns(columns)
    .filter((column) => {
      const meaning = isClassifiedColumn(column)
        ? column.standardField
        : `unknown:${column.displayName}`
      if (seenMeanings.has(meaning)) return false
      seenMeanings.add(meaning)
      return true
    })
    .slice(0, 6)
}
