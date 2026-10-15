import type {
  InsightReportResult,
  InsightResult,
} from '../src/api/analysis/insightTypes.ts'
import type { WorkbookQuestionAnswer } from '../src/api/analysis/questionTypes.ts'

export const questionAnswer = (
  overrides: Partial<WorkbookQuestionAnswer> = {},
): WorkbookQuestionAnswer => ({
  question: '매출 합계는?',
  answer: '검증되지 않은 이전 답변 999999',
  status: 'answered',
  confidence: 1,
  selectedTools: [],
  evidence: [
    {
      kind: 'cell',
      sheetName: '매출 현황',
      reference: 'B2',
      description: '설명은 전달하지 않음',
      value: 999999,
      formula: null,
      label: '매출',
    },
  ],
  limitations: [],
  ...overrides,
})

export const contextInsight = (
  overrides: Partial<InsightResult> = {},
): InsightResult => ({
  title: '매출 변화',
  topic: '매출',
  fact: '전달하지 않을 인사이트 사실 888888',
  cause: '전달하지 않을 원인',
  impact: null,
  recommendation: null,
  category: 'change',
  severity: 'info',
  evidence: ['매출 현황!B2:B4'],
  confidence: 1,
  isIncomplete: false,
  validationStatus: 'verified',
  validationReasons: [],
  ...overrides,
})

export const contextReport = (insights: InsightResult[]): InsightReportResult => ({
  overview: '전달하지 않을 전체 요약',
  insights,
  limitations: [],
  hasIncompleteData: false,
  validation: null,
})
