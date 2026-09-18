import type { WritebackChange } from '@/api/analysis'

/** 변경을 가리키는 키. 근거 셀 목록과 같은 `시트!셀` 형식을 쓴다. */
export const changeKey = (change: WritebackChange) =>
  `${change.sheetName}!${change.reference}`

export const allChangeKeys = (changes: WritebackChange[]) => changes.map(changeKey)

export const toggleChangeKey = (selected: string[], key: string) =>
  selected.includes(key) ? selected.filter((item) => item !== key) : [...selected, key]

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
