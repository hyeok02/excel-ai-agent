interface SummaryItem {
  label: string
  value: string
  helper: string
  accent?: string
}

interface SummaryCardsProps {
  items: SummaryItem[]
}

const SummaryCards = ({ items }: SummaryCardsProps) => {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {items.map((item, index) => (
        <article className="metric-card" key={item.label}>
          <div className="flex items-start justify-between">
            <p className="text-sm font-semibold text-slate-500">{item.label}</p>
            <span
              className="size-2 rounded-full"
              style={{
                backgroundColor: item.accent ?? ['#3182f6', '#8b5cf6', '#10b981'][index],
              }}
            />
          </div>
          <p className="mt-6 text-[2rem] font-extrabold tracking-[-0.04em] text-slate-950">
            {item.value}
          </p>
          <p className="mt-1 text-xs font-medium text-slate-400">{item.helper}</p>
        </article>
      ))}
    </section>
  )
}

export default SummaryCards
