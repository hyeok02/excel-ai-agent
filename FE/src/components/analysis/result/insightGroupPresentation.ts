import type { InsightResult } from '@/api/analysis/insightTypes'

export type InsightGroupKey = 'metric' | 'trend' | 'change' | 'anomaly' | 'additional'

export interface InsightGroup {
  key: InsightGroupKey
  title: string
  description: string
  insights: InsightResult[]
}

const GROUP_PRESENTATION: Pick<InsightGroup, 'key' | 'description'>[] = [
  {
    key: 'metric',
    description: '결론을 뒷받침하는 중요한 수치와 비교 결과입니다.',
  },
  {
    key: 'trend',
    description: '여러 시점에서 확인된 값의 흐름입니다.',
  },
  {
    key: 'change',
    description: '두 시점의 값을 비교한 변화입니다.',
  },
  {
    key: 'anomaly',
    description: '결론에 영향을 줄 수 있어 먼저 확인할 내용입니다.',
  },
  {
    key: 'additional',
    description: '결론을 이해하는 데 필요한 보조 내용입니다.',
  },
]

const topicHeading = (insights: InsightResult[], category: InsightGroupKey) => {
  const topics = [...new Set(insights.map((insight) => {
    if (insight.topic) return insight.topic
    return /^(?:원본에서 확인한 내용|인사이트 \d+)$/.test(insight.title)
      ? null
      : insight.title
  }).filter((topic): topic is string => topic !== null))]
  if (topics.length === 0) return '주제 확인 불가'
  if (topics.length > 2) return `${topics.slice(0, 2).join(' · ')} 외 ${topics.length - 2}개 주제`
  if (topics.length > 1) return topics.join(' · ')
  if (!insights[0].topic) return topics[0]
  if (category === 'trend') return `${topics[0]} 추이`
  if (category === 'change') return `${topics[0]} 증감`
  return topics[0]
}

const getGroupKey = (insight: InsightResult): InsightGroupKey => {
  if (insight.category === 'risk' || insight.severity !== 'info') return 'anomaly'
  if (insight.category === 'metric') return 'metric'
  if (insight.category === 'trend') return 'trend'
  if (insight.category === 'change') return 'change'
  return 'additional'
}

export const groupInsights = (insights: InsightResult[]): InsightGroup[] =>
  GROUP_PRESENTATION.flatMap((presentation) => {
    const selected = insights.filter((insight) => getGroupKey(insight) === presentation.key)
    return selected.length
      ? [{ ...presentation, title: topicHeading(selected, presentation.key), insights: selected }]
      : []
  })
