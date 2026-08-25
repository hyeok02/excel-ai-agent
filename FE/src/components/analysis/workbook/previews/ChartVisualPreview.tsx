import type { ChartResult } from '@/api/analysis'

interface ChartVisualPreviewProps {
  chart: ChartResult
}

const palette = ['#2563eb', '#14b8a6', '#8b5cf6', '#f59e0b']

const numericSeries = (chart: ChartResult) =>
  chart.series
    .slice(0, 4)
    .map((series) => ({
      title: series.title || '값',
      values: series.valueSamples
        .map((value, index) => ({
          value: typeof value === 'number' ? value : Number(value),
          category: series.categorySamples[index],
        }))
        .filter((entry) => Number.isFinite(entry.value)),
    }))
    .filter((series) => series.values.length > 0)

const ChartVisualPreview = ({ chart }: ChartVisualPreviewProps) => {
  const series = numericSeries(chart)
  if (series.length === 0) return null

  const chartType = chart.chartType.toLowerCase()
  const flatValues = series.flatMap((item) => item.values.map(({ value }) => value))
  const minimum = Math.min(0, ...flatValues)
  const maximum = Math.max(...flatValues)
  const span = Math.max(maximum - minimum, 1)
  const pointCount = Math.max(...series.map((item) => item.values.length))
  const plotWidth = 640
  const plotHeight = 190
  const paddingX = 26
  const paddingY = 18
  const usableWidth = plotWidth - paddingX * 2
  const usableHeight = plotHeight - paddingY * 2
  const y = (value: number) => paddingY + ((maximum - value) / span) * usableHeight

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="mb-2 flex flex-wrap gap-3 text-[10px] font-bold text-slate-500">
        {series.map((item, index) => (
          <span
            className="inline-flex items-center gap-1.5"
            key={`${item.title}-${index}`}
          >
            <i
              className="size-2 rounded-full"
              style={{ backgroundColor: palette[index] }}
            />
            {item.title}
          </span>
        ))}
      </div>
      <svg
        aria-label={`${chart.title || 'Excel 차트'} 미리보기`}
        className="h-52 w-full overflow-visible"
        role="img"
        viewBox={`0 0 ${plotWidth} ${plotHeight}`}
      >
        {[0, 0.5, 1].map((ratio) => {
          const lineY = paddingY + ratio * usableHeight
          return (
            <line
              key={ratio}
              stroke="#e2e8f0"
              strokeDasharray="3 5"
              x1={paddingX}
              x2={plotWidth - paddingX}
              y1={lineY}
              y2={lineY}
            />
          )
        })}

        {chartType.includes('bar')
          ? series.flatMap((item, seriesIndex) =>
              item.values.map(({ value }, valueIndex) => {
                const groupWidth = usableWidth / Math.max(pointCount, 1)
                const barWidth = Math.max(4, (groupWidth * 0.72) / series.length)
                const baseY = y(0)
                const valueY = y(value)
                return (
                  <rect
                    fill={palette[seriesIndex]}
                    height={Math.max(Math.abs(baseY - valueY), 1)}
                    key={`${seriesIndex}-${valueIndex}`}
                    opacity="0.88"
                    rx="2"
                    width={barWidth}
                    x={
                      paddingX +
                      valueIndex * groupWidth +
                      groupWidth * 0.14 +
                      seriesIndex * barWidth
                    }
                    y={Math.min(baseY, valueY)}
                  />
                )
              }),
            )
          : series.map((item, seriesIndex) => {
              const points = item.values
                .map(({ value }, index) => {
                  const x =
                    paddingX + (index / Math.max(item.values.length - 1, 1)) * usableWidth
                  return `${x},${y(value)}`
                })
                .join(' ')
              return (
                <g key={`${item.title}-${seriesIndex}`}>
                  <polyline
                    fill="none"
                    points={points}
                    stroke={palette[seriesIndex]}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="3"
                  />
                  {item.values.map(({ value }, index) => {
                    const x =
                      paddingX +
                      (index / Math.max(item.values.length - 1, 1)) * usableWidth
                    return (
                      <circle
                        cx={x}
                        cy={y(value)}
                        fill="white"
                        key={index}
                        r="3.5"
                        stroke={palette[seriesIndex]}
                        strokeWidth="2"
                      />
                    )
                  })}
                </g>
              )
            })}
      </svg>
      <p className="mt-1 text-center text-[10px] text-slate-400">
        Excel 원본 계열의 앞쪽 표본값으로 재구성한 미리보기입니다.
      </p>
    </div>
  )
}

export default ChartVisualPreview
