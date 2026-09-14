export const INSIGHT_EVIDENCE_PREVIEW_LIMIT = 2

export interface InsightEvidenceLocation {
  raw: string
  sheetName: string | null
  cellRange: string | null
}

export interface InsightEvidenceGroup {
  sheetName: string | null
  locations: InsightEvidenceLocation[]
}

export const insightEvidenceDisclosureLabel = (count: number) =>
  `원본 근거 ${count}개 위치 보기`

export const parseInsightEvidenceLocation = (raw: string): InsightEvidenceLocation => {
  const separatorIndex = raw.lastIndexOf('!')
  if (separatorIndex <= 0 || separatorIndex === raw.length - 1) {
    return { raw, sheetName: null, cellRange: null }
  }

  const sheetPart = raw.slice(0, separatorIndex)
  const quoted = sheetPart.startsWith("'") && sheetPart.endsWith("'")
  const sheetName = quoted ? sheetPart.slice(1, -1).replaceAll("''", "'") : sheetPart
  const cellRange = raw.slice(separatorIndex + 1)

  return sheetName && cellRange
    ? { raw, sheetName, cellRange }
    : { raw, sheetName: null, cellRange: null }
}

export const prepareInsightEvidence = (
  evidence: string[],
  expanded: boolean,
  previewLimit = INSIGHT_EVIDENCE_PREVIEW_LIMIT,
) => {
  const locations = Array.from(
    new Set(evidence.map((location) => location.trim()).filter(Boolean)),
  ).map(parseInsightEvidenceLocation)
  const visibleLocations = expanded ? locations : locations.slice(0, previewLimit)

  return {
    visibleLocations,
    hiddenCount: Math.max(0, locations.length - previewLimit),
  }
}

export const groupInsightEvidence = (
  locations: InsightEvidenceLocation[],
): InsightEvidenceGroup[] => {
  const groups = new Map<string | null, InsightEvidenceGroup>()
  for (const location of locations) {
    let group = groups.get(location.sheetName)
    if (!group) {
      group = { sheetName: location.sheetName, locations: [] }
      groups.set(location.sheetName, group)
    }
    group.locations.push(location)
  }
  return [...groups.values()]
}

export const compactInsightEvidenceRanges = (
  locations: InsightEvidenceLocation[],
): string[] => {
  const bands = new Map<string, { firstIndex: number; rows: number[]; start: string; end: string }>()
  const results: { firstIndex: number; text: string }[] = []

  locations.forEach((location, index) => {
    const range = location.cellRange
    const match = range?.match(/^(\$?[A-Z]{1,3})([1-9]\d*)(?::(\$?[A-Z]{1,3})([1-9]\d*))?$/i)
    if (!match || (match[4] && match[2] !== match[4])) {
      results.push({ firstIndex: index, text: range ?? location.raw })
      return
    }

    const start = match[1].toUpperCase()
    const end = (match[3] ?? match[1]).toUpperCase()
    const key = `${start}:${end}`
    const band = bands.get(key) ?? { firstIndex: index, rows: [], start, end }
    band.rows.push(Number(match[2]))
    bands.set(key, band)
  })

  for (const band of bands.values()) {
    const rows = [...new Set(band.rows)].sort((left, right) => left - right)
    let startRow = rows[0]
    let endRow = rows[0]

    const addRange = () => {
      const text = band.start === band.end && startRow === endRow
        ? `${band.start}${startRow}`
        : `${band.start}${startRow}:${band.end}${endRow}`
      results.push({ firstIndex: band.firstIndex, text })
    }

    for (const row of rows.slice(1)) {
      if (row === endRow + 1) {
        endRow = row
      } else {
        addRange()
        startRow = row
        endRow = row
      }
    }
    addRange()
  }

  return results.sort((left, right) => left.firstIndex - right.firstIndex).map(({ text }) => text)
}
