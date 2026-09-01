const GENERIC_INPUTS = new Set([
  '안녕',
  '응',
  '예',
  '아니',
  '뭐',
  '질문',
  '테스트',
  '도와줘',
  'hello',
  'test',
  'ok',
  'okay',
])

const SPECIFIC_TERMS = [
  '요약',
  '분석',
  '알려',
  '보여',
  '찾아',
  '확인',
  '검토',
  '비교',
  '계산',
  '설명',
  '얼마',
  '몇',
  '무엇',
  '무슨',
  '왜',
  '어떻게',
  '어디',
  '언제',
  '어때',
  '추이',
  '증가',
  '감소',
  '변화',
  '오류',
  '위험',
  '수식',
  '참조',
  '매출',
  '비용',
  '이익',
  '직원',
  '인원',
  '부서',
  '투자',
  '거래',
  '날짜',
  '기간',
  '합계',
  '평균',
  '최대',
  '최소',
  '값',
  '셀',
  '시트',
  '파일',
  '워크북',
  'what',
  'which',
  'how',
  'why',
  'show',
  'find',
  'summary',
  'analy',
  'compare',
  'formula',
  'cell',
  'sheet',
  'revenue',
  'sales',
  'employee',
  'headcount',
  'investment',
]

export const getQuestionValidationMessage = (question: string) => {
  const normalized = question.trim()
  const meaningful = normalized.replace(/[^0-9A-Za-z가-힣]/g, '').toLocaleLowerCase()
  const repeatedCharacter = meaningful.length < 4 && new Set(meaningful).size === 1
  const hasCellReference = /\b[a-z]{1,3}\$?\d+\b/i.test(normalized)
  const hasSpecificTerm = SPECIFIC_TERMS.some((term) => meaningful.includes(term))
  if (
    !meaningful ||
    GENERIC_INPUTS.has(meaningful) ||
    repeatedCharacter ||
    (!hasCellReference && (meaningful.length < 3 || !hasSpecificTerm))
  ) {
    return '질문이 구체적이지 않아 무엇을 확인해야 할지 모르겠습니다. 확인할 항목이나 기간을 포함해 다시 질문해주세요.'
  }
  return null
}
