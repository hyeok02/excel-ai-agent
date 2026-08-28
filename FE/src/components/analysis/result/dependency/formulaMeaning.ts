const hasFunction = (formula: string, name: string) =>
  new RegExp(`(?:^|[^A-Z0-9_.])${name}\\s*\\(`, 'i').test(formula)

export const describeFormulaMeaning = (formula: string | null) => {
  if (!formula) return '참조한 값을 이용해 계산 결과를 만듭니다.'

  const usesCondition = hasFunction(formula, 'IF') || hasFunction(formula, 'IFS')
  const usesSum = hasFunction(formula, 'SUM') || hasFunction(formula, 'SUMIF')
  const usesLookup = ['XLOOKUP', 'VLOOKUP', 'HLOOKUP', 'INDEX', 'MATCH'].some((name) =>
    hasFunction(formula, name),
  )
  const joinsText = formula.includes('&') || hasFunction(formula, 'TEXTJOIN')

  if (usesCondition && usesSum && joinsText) {
    return '입력 범위의 합계를 확인한 뒤, 조건에 따라 대체 값을 사용하거나 여러 텍스트를 합쳐 결과를 만듭니다.'
  }
  if (usesCondition && usesLookup) {
    return '조건을 확인한 뒤 다른 표에서 알맞은 값을 찾아 결과로 사용합니다.'
  }
  if (usesCondition && usesSum) {
    return '입력 범위의 합계를 확인하고 조건에 따라 표시할 결과를 선택합니다.'
  }
  if (usesCondition && joinsText) {
    return '조건을 확인한 뒤 필요한 텍스트를 연결해 결과를 만듭니다.'
  }
  if (usesLookup) return '다른 표나 범위에서 조건에 맞는 값을 찾아옵니다.'
  if (joinsText) return '여러 셀의 텍스트를 하나의 결과로 연결합니다.'
  if (usesSum) return '여러 입력 값을 합산해 결과를 계산합니다.'
  if (usesCondition) return '입력 조건에 따라 서로 다른 결과를 선택합니다.'

  return '참조한 입력 값을 이용해 계산 결과를 만듭니다.'
}
