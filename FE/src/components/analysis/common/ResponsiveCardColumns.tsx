import { Fragment, type Key, type ReactNode } from 'react'

import { cn } from '@/utils/cn'

type Breakpoint = 'md' | 'lg' | 'xl'
type Density = 'compact' | 'normal'

interface ResponsiveCardColumnsProps<T> {
  breakpoint?: Breakpoint
  className?: string
  density?: Density
  getKey: (item: T, index: number) => Key
  items: T[]
  renderItem: (item: T, index: number) => ReactNode
}

const breakpointClasses = {
  md: { single: 'md:hidden', columns: 'hidden md:grid' },
  lg: { single: 'lg:hidden', columns: 'hidden lg:grid' },
  xl: { single: 'xl:hidden', columns: 'hidden xl:grid' },
} as const

const densityClasses = {
  compact: { gap: 'gap-2', stack: 'space-y-2' },
  normal: { gap: 'gap-3', stack: 'space-y-3' },
} as const

const ResponsiveCardColumns = <T,>({
  breakpoint = 'lg',
  className,
  density = 'normal',
  getKey,
  items,
  renderItem,
}: ResponsiveCardColumnsProps<T>) => {
  const entries = items.map((item, index) => ({ item, index }))
  const leftEntries = entries.filter(({ index }) => index % 2 === 0)
  const rightEntries = entries.filter(({ index }) => index % 2 === 1)
  const layout = breakpointClasses[breakpoint]
  const spacing = densityClasses[density]
  const renderEntries = (
    selectedEntries: typeof entries,
    column: 'left' | 'right' | 'single',
  ) =>
    selectedEntries.map(({ item, index }) => (
      <Fragment key={`${column}-${String(getKey(item, index))}`}>
        {renderItem(item, index)}
      </Fragment>
    ))

  return (
    <div className={className}>
      <div className={cn(layout.single, spacing.stack)}>
        {renderEntries(entries, 'single')}
      </div>
      <div className={cn(layout.columns, 'grid-cols-2 items-start', spacing.gap)}>
        <div className={spacing.stack}>{renderEntries(leftEntries, 'left')}</div>
        <div className={spacing.stack}>{renderEntries(rightEntries, 'right')}</div>
      </div>
    </div>
  )
}

export default ResponsiveCardColumns
