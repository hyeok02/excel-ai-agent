import type { WritebackChange, WritebackRelatedCell } from '@/api/analysis'

/** 변경을 가리키는 키. 근거 셀 목록과 같은 `시트!셀` 형식을 쓴다. */
export const changeKey = (change: WritebackChange) =>
  `${change.sheetName}!${change.reference}`

export const relatedKey = (related: WritebackRelatedCell) =>
  `${related.sheetName}!${related.reference}`

const relatedOf = (change: WritebackChange) => change.relatedCells ?? []

/** 변경과 그에 딸린 관련 셀을 모두 합한 승인 후보. 같은 셀은 한 번만 센다. */
export const allChangeKeys = (changes: WritebackChange[]) => [
  ...new Set(
    changes.flatMap((change) => [
      changeKey(change),
      ...relatedOf(change).map(relatedKey),
    ]),
  ),
]

export const toggleChangeKey = (selected: string[], key: string) =>
  selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key]

/**
 * 선택을 바꾼 뒤, 본 변경이 빠지면 그에 딸린 관련 셀도 함께 뺀다.
 * 관련 셀은 본 변경이 있어야 의미가 있어 단독으로는 승인할 수 없다.
 */
export const toggleSelection = (
  changes: WritebackChange[],
  selected: string[],
  key: string,
) => {
  const next = new Set(toggleChangeKey(selected, key))
  const kept = new Set(changes.map(changeKey).filter((item) => next.has(item)))
  for (const change of changes) {
    if (next.has(changeKey(change))) continue
    for (const related of relatedOf(change)) {
      if (!kept.has(relatedKey(related))) next.delete(relatedKey(related))
    }
  }
  return [...next]
}

/** 본 변경은 승인했는데 함께 확인할 셀을 빼둔 경우를 찾는다. */
export const unselectedRelated = (changes: WritebackChange[], selected: string[]) => {
  const chosen = new Set(selected)
  const left: string[] = []
  for (const change of changes) {
    if (!chosen.has(changeKey(change))) continue
    for (const related of relatedOf(change)) {
      if (!chosen.has(relatedKey(related))) left.push(relatedKey(related))
    }
  }
  return [...new Set(left)]
}

/**
 * 한쪽만 승인하면 결과가 미리보기와 달라지는 변경 쌍을 찾는다.
 * 변경 A가 바꾸는 셀을 변경 B의 셀이 수식으로 참조하는데,
 * 둘 중 하나만 선택됐다면 B는 미리보기와 다른 값으로 계산된다.
 */
export const brokenDependencies = (changes: WritebackChange[], selected: string[]) => {
  const chosen = new Set(selected)
  const byKey = new Map(changes.map((change) => [changeKey(change), change]))
  const broken = new Set<string>()

  for (const change of changes) {
    const source = changeKey(change)
    for (const affected of change.affectedCells ?? []) {
      if (!byKey.has(affected)) continue
      if (chosen.has(source) === chosen.has(affected)) continue
      broken.add(chosen.has(source) ? affected : source)
    }
  }
  return [...broken]
}

export const approvalButtonLabel = (selectedCount: number, totalCount: number) => {
  if (selectedCount === totalCount) return '승인하고 수정본 만들기'
  return `선택한 ${selectedCount}개만 승인하고 수정본 만들기`
}
