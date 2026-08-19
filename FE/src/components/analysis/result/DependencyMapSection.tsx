import { ArrowRight, Braces, GitBranch, Network, Waypoints } from 'lucide-react'

import type {
  DependencyClusterResult,
  DependencyEdgeResult,
  DependencyGraphResult,
  DependencyNodeResult,
} from '@/api/analysis'

interface DependencyMapSectionProps {
  graph: DependencyGraphResult
}

interface ParsedCellLabel {
  sheet: string
  column: string
  row: number
}

interface RelationshipGroup {
  target: DependencyNodeResult | null
  targetLabel: string
  sourceLabels: string[]
  sourceCount: number
  crossSheet: boolean
}

const CELL_LABEL_PATTERN = /^(.*)!\$?([A-Z]{1,3})\$?(\d+)$/i

const parseCellLabel = (label: string): ParsedCellLabel | null => {
  const match = label.match(CELL_LABEL_PATTERN)
  if (!match) return null

  return {
    sheet: match[1],
    column: match[2].toUpperCase(),
    row: Number(match[3]),
  }
}

const compressCellLabels = (labels: string[]) => {
  const cellGroups = new Map<string, ParsedCellLabel[]>()
  const otherLabels: string[] = []

  labels.forEach((label) => {
    const parsed = parseCellLabel(label)
    if (!parsed) {
      otherLabels.push(label)
      return
    }

    const key = `${parsed.sheet}\u0000${parsed.column}`
    const group = cellGroups.get(key) ?? []
    group.push(parsed)
    cellGroups.set(key, group)
  })

  const ranges = [...cellGroups.values()].flatMap((group) => {
    const sortedRows = [...new Set(group.map(({ row }) => row))].sort((a, b) => a - b)
    if (sortedRows.length === 0) return []

    const { sheet, column } = group[0]
    const compressed: string[] = []
    let start = sortedRows[0]
    let end = sortedRows[0]

    sortedRows.slice(1).forEach((row) => {
      if (row === end + 1) {
        end = row
        return
      }

      compressed.push(
        start === end
          ? `${sheet}!${column}${start}`
          : `${sheet}!${column}${start}:${column}${end}`,
      )
      start = row
      end = row
    })

    compressed.push(
      start === end
        ? `${sheet}!${column}${start}`
        : `${sheet}!${column}${start}:${column}${end}`,
    )
    return compressed
  })

  return [...ranges, ...otherLabels]
}

const getNode = (cluster: DependencyClusterResult, nodeId: string) =>
  cluster.nodes.find((node) => node.id === nodeId) ?? null

const getNodeLabel = (cluster: DependencyClusterResult, nodeId: string) =>
  getNode(cluster, nodeId)?.label ?? nodeId

const groupRelationships = (cluster: DependencyClusterResult): RelationshipGroup[] => {
  const groups = new Map<
    string,
    { edges: DependencyEdgeResult[]; sources: Set<string>; crossSheet: boolean }
  >()

  cluster.edges.forEach((edge) => {
    const group = groups.get(edge.target) ?? {
      edges: [],
      sources: new Set<string>(),
      crossSheet: false,
    }
    group.edges.push(edge)
    group.sources.add(getNodeLabel(cluster, edge.source))
    group.crossSheet ||= edge.crossSheet
    groups.set(edge.target, group)
  })

  return [...groups.entries()]
    .map(([targetId, group]) => ({
      target: getNode(cluster, targetId),
      targetLabel: getNodeLabel(cluster, targetId),
      sourceLabels: compressCellLabels([...group.sources]),
      sourceCount: group.sources.size,
      crossSheet: group.crossSheet,
    }))
    .sort((left, right) => right.sourceCount - left.sourceCount)
}

const shortLocation = (label: string, sharedSheet?: string) => {
  if (!sharedSheet || !label.startsWith(`${sharedSheet}!`)) return label
  return label.slice(sharedSheet.length + 1)
}

const RelationshipRow = ({ relationship }: { relationship: RelationshipGroup }) => {
  const targetCell = parseCellLabel(relationship.targetLabel)
  const sharedSheet =
    targetCell &&
    relationship.sourceLabels.every((label) => parseCellLabel(label)?.sheet === targetCell.sheet)
      ? targetCell.sheet
      : undefined
  const visibleSources = relationship.sourceLabels.slice(0, 3)
  const sourceText = visibleSources
    .map((label) => shortLocation(label, sharedSheet))
    .join(', ')
  const hiddenSourceCount = relationship.sourceLabels.length - visibleSources.length
  const targetText = shortLocation(relationship.targetLabel, sharedSheet)

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="grid items-center gap-3 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.12em] text-slate-400">
            입력·참조 범위
          </p>
          <code className="mt-1 block truncate text-xs font-bold text-slate-700" title={sourceText}>
            {sourceText}
            {hiddenSourceCount > 0 ? ` 외 ${hiddenSourceCount}개 범위` : ''}
          </code>
        </div>
        <span className="grid size-8 place-items-center rounded-full bg-brand-50 text-brand-600">
          <ArrowRight aria-hidden="true" size={15} />
        </span>
        <div className="min-w-0">
          <p className="text-[10px] font-extrabold tracking-[0.12em] text-slate-400">
            계산 결과 셀
          </p>
          <code className="mt-1 block truncate text-xs font-extrabold text-slate-900" title={targetText}>
            {targetText}
          </code>
        </div>
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-500">
        {sharedSheet ? `${sharedSheet} 시트에서 ` : ''}
        <strong className="font-bold text-slate-700">{sourceText}</strong>의 값이 바뀌면{' '}
        <strong className="font-bold text-slate-900">{targetText}</strong> 계산 결과가 영향을 받을 수 있어요.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {relationship.crossSheet && (
          <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-[10px] font-bold text-brand-700">
            다른 시트 참조
          </span>
        )}
        {relationship.sourceCount > 1 && (
          <span className="rounded-lg bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
            {relationship.sourceCount.toLocaleString()}개 셀 참조
          </span>
        )}
      </div>

      {relationship.target?.formula && (
        <details className="mt-3 rounded-xl bg-slate-50 px-3 py-2">
          <summary className="cursor-pointer list-none text-[11px] font-bold text-slate-500 marker:hidden">
            실제 수식 보기
          </summary>
          <code className="mt-2 block break-all text-[11px] leading-5 text-slate-600">
            {relationship.target.formula}
          </code>
        </details>
      )}
    </div>
  )
}

const DependencyClusterCard = ({ cluster }: { cluster: DependencyClusterResult }) => {
  const relationships = groupRelationships(cluster)
  const visibleRelationships = relationships.slice(0, 4)
  const sheetDescription =
    cluster.sheetNames.length === 1
      ? `${cluster.sheetNames[0]} 시트의 주요 계산 흐름`
      : `${cluster.sheetNames.length}개 시트가 연결된 계산 흐름`

  return (
    <article className="rounded-3xl border border-slate-200 bg-slate-50/60 p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-sm font-extrabold text-slate-950">{sheetDescription}</h4>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {cluster.formulaCount.toLocaleString()}개 수식이{' '}
            {cluster.nodeCount.toLocaleString()}개 관련 셀과 연결되어 있어요.
          </p>
        </div>
        <span className="rounded-xl bg-white px-3 py-2 text-[11px] font-bold text-slate-500 shadow-sm">
          주요 영향 관계 {relationships.length.toLocaleString()}개
        </span>
      </div>

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        {visibleRelationships.map((relationship) => (
          <RelationshipRow
            key={`${relationship.targetLabel}-${relationship.sourceLabels.join('|')}`}
            relationship={relationship}
          />
        ))}
      </div>

      {(cluster.truncated || relationships.length > visibleRelationships.length) && (
        <p className="mt-4 text-[11px] leading-5 text-slate-400">
          복잡한 계산 묶음은 영향이 큰 대표 관계만 보여줘요. 전체 개수에는 모든 셀과 수식이 반영됩니다.
        </p>
      )}
    </article>
  )
}

const DependencyMapSection = ({ graph }: DependencyMapSectionProps) => {
  const summaryItems = [
    { label: '관련 셀', value: graph.nodeCount, icon: Network },
    { label: '수식 셀', value: graph.formulaNodeCount, icon: Braces },
    { label: '참조 관계', value: graph.edgeCount, icon: GitBranch },
    { label: '시트 간 참조', value: graph.crossSheetEdgeCount, icon: Waypoints },
  ] as const

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-brand-100 bg-gradient-to-r from-brand-50/80 to-white p-5 md:p-6">
        <div>
          <div className="flex items-center gap-2 text-brand-700">
            <Network aria-hidden="true" size={18} />
            <span className="text-xs font-extrabold tracking-[0.16em]">FORMULA IMPACT</span>
          </div>
          <h3 className="mt-2 text-lg font-extrabold text-slate-950">수식 영향 관계</h3>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            어떤 입력 셀과 범위가 계산 결과에 영향을 주는지 이해하기 쉽게 정리했어요.
          </p>
        </div>
        <span className="rounded-xl border border-brand-100 bg-white px-3 py-2 text-xs font-bold text-brand-700 shadow-sm">
          계산 흐름 {graph.clusterCount.toLocaleString()}개
        </span>
      </div>

      <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4 md:p-6">
        {summaryItems.map(({ label, value, icon: Icon }) => (
          <div className="rounded-2xl bg-slate-50 p-4" key={label}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold text-slate-400">{label}</p>
              <Icon aria-hidden="true" className="text-brand-500" size={16} />
            </div>
            <p className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
              {value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {graph.clusters.length > 0 && (
        <div className="space-y-4 px-5 pb-5 md:px-6 md:pb-6">
          {graph.clusters.slice(0, 4).map((cluster) => (
            <DependencyClusterCard cluster={cluster} key={cluster.id} />
          ))}
          {graph.clusters.length > 4 && (
            <p className="text-center text-[11px] text-slate-400">
              영향도가 큰 계산 흐름 4개를 우선 표시했습니다.
            </p>
          )}
        </div>
      )}
    </section>
  )
}

export default DependencyMapSection
