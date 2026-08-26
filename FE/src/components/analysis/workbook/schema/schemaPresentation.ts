export const STANDARD_FIELD_LABELS: Record<string, string> = {
  amount: '금액',
  category: '분류',
  cost: '비용',
  headcount: '인원',
  metric: '측정값',
  period: '기간',
  profit: '이익',
  profit_margin: '이익률',
  quantity: '수량',
  rate: '비율',
  revenue: '매출',
  unknown: '미분류',
}

export const DATA_TYPE_LABELS: Record<string, string> = {
  boolean: '참·거짓',
  date: '날짜형',
  empty: '빈 값',
  mixed: '혼합형',
  number: '숫자형',
  text: '문자형',
}

export const UNIT_TYPE_LABELS: Record<string, string> = {
  currency: '통화',
  date: '날짜',
  headcount: '인원',
  none: '단위 없음',
  percentage: '비율',
  quantity: '수량',
}

export const labelFor = (labels: Record<string, string>, value: string) =>
  labels[value] ?? value
