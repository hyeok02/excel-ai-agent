export const getQuestionValidationMessage = (question: string) => {
  const normalized = question.trim()
  const meaningful = normalized.replace(/[^0-9A-Za-zㄱ-ㅣ가-힣]/g, '')
  if (meaningful.length < 2) return '두 글자 이상의 질문을 입력해주세요.'
  const repeatedPattern = /^(.{1,4})\1{2,}$/u.test(meaningful)
  const jamoOnly = /^[ㄱ-ㅣ]+$/.test(meaningful)
  if (repeatedPattern || jamoOnly) {
    return '의미 있는 단어나 문장으로 질문해주세요.'
  }
  return null
}
