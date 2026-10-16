import type {
  WorkbookQuestionAnswer,
  WorkbookQuestionHistoryPage,
} from '../src/api/analysis/questionTypes.ts'
import {
  createQuestionSession,
  reduceQuestionSession,
} from '../src/hooks/analysis/questionSession.ts'
import { questionAnswer } from './questionContext.fixtures.ts'

export const historyPage = (
  answers: WorkbookQuestionAnswer[],
  nextCursor: string | null = null,
): WorkbookQuestionHistoryPage => ({
  items: answers.map((answer, index) => ({
    id: String(index + 1),
    createdAt: '2026-10-16T01:00:00Z',
    answer,
  })),
  nextCursor,
})

export const numberedAnswer = (number: number) =>
  questionAnswer({
    question: `질문 ${number}`,
    resolvedQuestion: `회사 A의 ${number}월 매출은?`,
  })

export const restoredSession = (
  answers: WorkbookQuestionAnswer[] = [numberedAnswer(3), numberedAnswer(4)],
  nextCursor: string | null = '3',
) => {
  const session = createQuestionSession('analysis-a', 'owner-a')
  return reduceQuestionSession(session, {
    scope: session.scope,
    type: 'restoreSuccess',
    page: historyPage(answers, nextCursor),
  })
}
