/** 근거 목록이 길어지면 처음 일부만 보여주고 나머지는 접어 둔다. */
export const EVIDENCE_PREVIEW_LIMIT = 12

export const limitEvidence = <T>(
  items: T[],
  expanded: boolean,
  limit = EVIDENCE_PREVIEW_LIMIT,
) => ({
  visible: expanded ? items : items.slice(0, limit),
  hiddenCount: Math.max(0, items.length - limit),
})

export const evidenceToggleLabel = (expanded: boolean, hiddenCount: number) =>
  expanded ? '근거 접기' : `나머지 ${hiddenCount}개 더 보기`
