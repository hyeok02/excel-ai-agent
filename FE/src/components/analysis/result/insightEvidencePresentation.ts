export const INSIGHT_EVIDENCE_PREVIEW_LIMIT = 2

export interface InsightEvidenceLocation {
  raw: string
  sheetName: string | null
  cellRange: string | null
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
