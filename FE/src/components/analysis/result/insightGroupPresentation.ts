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
    description: '결론을 뒷받침하는 중요한 수치와 비교 결과입니다.',
  },
  {
    key: 'trend',
    title: '추세',
    description: '시간에 따라 달라진 핵심 흐름입니다.',
  },
  {
    key: 'anomaly',
    title: '이상징후',
    description: '결론에 영향을 줄 수 있어 먼저 확인할 내용입니다.',
  },
  {
    key: 'additional',
    title: '추가 내용',
    description: '결론을 이해하는 데 필요한 보조 내용입니다.',
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
