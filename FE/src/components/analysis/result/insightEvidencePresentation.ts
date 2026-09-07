export const INSIGHT_EVIDENCE_PREVIEW_LIMIT = 2

export const prepareInsightEvidence = (
  evidence: string[],
  expanded: boolean,
  previewLimit = INSIGHT_EVIDENCE_PREVIEW_LIMIT,
) => {
  const locations = Array.from(
    new Set(evidence.map((location) => location.trim()).filter(Boolean)),
  )
  const visibleLocations = expanded ? locations : locations.slice(0, previewLimit)

  return {
    visibleLocations,
    hiddenCount: Math.max(0, locations.length - previewLimit),
  }
}
