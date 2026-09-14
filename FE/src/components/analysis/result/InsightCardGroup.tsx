import InsightCard from '@/components/analysis/result/InsightCard'
import type { InsightGroup } from '@/components/analysis/result/insightGroupPresentation'

const InsightCardGroup = ({ group }: { group: InsightGroup }) => {
  return (
    <>
      {group.insights.map((insight, index) => {
        const title = group.insights.length === 1 ? group.title : insight.title
        const headingId = `insight-${group.key}-${index}`
        return (
          <section
            aria-labelledby={headingId}
            className="flex min-w-0 flex-col"
            key={headingId}
          >
            <div className="mb-3">
              <h4
                className="text-lg font-extrabold leading-7 text-slate-900"
                id={headingId}
              >
                {title}
              </h4>
              <p className="mt-0.5 text-xs text-slate-500">{group.description}</p>
            </div>
            <InsightCard insight={insight} showTitle={title !== insight.title} />
          </section>
        )
      })}
    </>
  )
}

export default InsightCardGroup
