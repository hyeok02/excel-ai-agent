import type { RegionResult } from '@/api/analysis'

export const safeRegionCount = (value: number | undefined | null) =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

export const regionSizeLabel = (region: RegionResult) => {
  const rows = safeRegionCount(region.rowCount)
  const columns = safeRegionCount(region.columnCount)
  const cells =
    safeRegionCount(region.cellCount) ??
    (rows !== null && columns !== null ? rows * columns : null)
  const dimensions =
    rows !== null && columns !== null ? `${rows}행 × ${columns}열` : '크기 정보 없음'
  const cellCount = cells !== null ? ` · ${cells.toLocaleString()}셀` : ''

  return `${dimensions}${cellCount}`
}
