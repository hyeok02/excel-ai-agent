import type { ColumnSchemaResult } from '@/api/analysis'

export type ColumnSchemaView = 'important' | 'review' | 'all'

export const isClassifiedColumn = (column: ColumnSchemaResult) =>
  column.standardField !== 'unknown'

export const hasDetectedUnit = (column: ColumnSchemaResult) =>
  column.unitType !== 'none'

export const needsColumnReview = (column: ColumnSchemaResult) =>
  !isClassifiedColumn(column) || column.confidence < 0.65

export const prioritizeColumns = (columns: ColumnSchemaResult[]) =>
  [...columns].sort((left, right) => {
    const leftScore =
      Number(isClassifiedColumn(left)) * 2 +
      Number(hasDetectedUnit(left)) +
      left.confidence
    const rightScore =
      Number(isClassifiedColumn(right)) * 2 +
      Number(hasDetectedUnit(right)) +
      right.confidence
    return rightScore - leftScore
  })

export const columnsForView = (
  columns: ColumnSchemaResult[],
  view: ColumnSchemaView,
) => {
  if (view === 'review') return columns.filter(needsColumnReview)
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
