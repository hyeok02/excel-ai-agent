import InsightCard from '@/components/analysis/result/InsightCard'
import type { InsightGroup } from '@/components/analysis/result/insightGroupPresentation'

const InsightCardGroup = ({ group }: { group: InsightGroup }) => {
  const rows = Array.from(
    { length: Math.ceil(group.insights.length / 2) },
    (_, rowIndex) => group.insights.slice(rowIndex * 2, rowIndex * 2 + 2),
  )

  return (
    <section aria-labelledby={`insight-group-${group.key}`}>
      <div className="mb-3">
        <h4
          className="text-sm font-extrabold text-slate-900"
          id={`insight-group-${group.key}`}
        >
          {group.title}
        </h4>
        <p className="mt-0.5 text-xs text-slate-500">{group.description}</p>
      </div>
      <div className="space-y-3">
        {rows.map((row, rowIndex) => (
          <div className="insight-card-row" key={`${group.key}-${rowIndex}`}>
            {row.map((insight, columnIndex) => (
              <InsightCard
                insight={insight}
                key={`${insight.title}-${rowIndex * 2 + columnIndex}`}
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}

export default InsightCardGroup
