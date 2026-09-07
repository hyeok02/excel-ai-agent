import type { InsightResult } from '@/api/analysis/insightTypes'

export type InsightGroupKey = 'metric' | 'trend' | 'anomaly' | 'additional'

export interface InsightGroup {
  key: InsightGroupKey
  title: string
  description: string
  insights: InsightResult[]
}

const GROUP_PRESENTATION: Omit<InsightGroup, 'insights'>[] = [
  {
    key: 'metric',
    title: '핵심 지표',
    description: '원본 값에서 확인한 대표 수치입니다.',
  },
  {
    key: 'trend',
    title: '추세',
    description: '비교 가능한 시점 사이의 변화를 정리했습니다.',
  },
  {
    key: 'anomaly',
    title: '이상징후',
    description: '원본 근거를 바탕으로 추가 검토가 필요한 내용입니다.',
  },
  {
    key: 'additional',
    title: '추가 내용',
    description: '파일에서 확인한 주요 내용을 정리했습니다.',
  },
]

const getGroupKey = (insight: InsightResult): InsightGroupKey => {
  if (insight.category === 'risk' || insight.severity !== 'info') return 'anomaly'
  if (insight.category === 'metric') return 'metric'
  if (insight.category === 'trend') return 'trend'
  return 'additional'
}

export const groupInsights = (insights: InsightResult[]): InsightGroup[] =>
  GROUP_PRESENTATION.map((presentation) => ({
    ...presentation,
    insights: insights.filter((insight) => getGroupKey(insight) === presentation.key),
  })).filter((group) => group.insights.length > 0)
