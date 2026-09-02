import type { ComponentProps, ReactNode } from 'react'

import SummaryCards from '@/components/common/SummaryCards'

interface WorkspaceOverviewPageProps {
  children: ReactNode
  description: string
  eyebrow: string
  summaryItems: ComponentProps<typeof SummaryCards>['items']
  title: string
}

const WorkspaceOverviewPage = ({
  children,
  description,
  eyebrow,
  summaryItems,
  title,
}: WorkspaceOverviewPageProps) => {
  return (
    <div className="space-y-6">
      <section className="panel page-reveal flex flex-wrap items-start justify-between gap-4 p-6 md:p-8">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="page-title">{title}</h1>
          <p className="page-description">{description}</p>
        </div>
      </section>

      <div className="page-reveal page-reveal-delay-1">
        <SummaryCards items={summaryItems} />
      </div>

      <div className="page-reveal page-reveal-delay-2">{children}</div>
    </div>
  )
}

export default WorkspaceOverviewPage
