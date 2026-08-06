interface SummaryItem {
  label: string
  value: string
  helper: string
}

interface SummaryCardsProps {
  items: SummaryItem[]
}

const SummaryCards = ({ items }: SummaryCardsProps) => {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {items.map((item) => (
        <article className="panel p-5" key={item.label}>
          <p className="text-sm text-slate-500">{item.label}</p>
          <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
            {item.value}
          </p>
          <p className="mt-1 text-xs text-slate-400">{item.helper}</p>
        </article>
      ))}
    </section>
  )
}

export default SummaryCards
