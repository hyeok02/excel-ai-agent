import type {
  DependencyClusterResult,
  DependencyEdgeResult,
  DependencyNodeResult,
} from '@/api/analysis'

export interface ParsedCellLabel {
  sheet: string
  column: string
  row: number
}

export interface RelationshipGroup {
  target: DependencyNodeResult | null
  targetLabel: string
  sourceLabels: string[]
  sourceCount: number
  crossSheet: boolean
}

const CELL_LABEL_PATTERN = /^(.*)!\$?([A-Z]{1,3})\$?(\d+)$/i

export const parseCellLabel = (label: string): ParsedCellLabel | null => {
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

export const groupRelationships = (
  cluster: DependencyClusterResult,
): RelationshipGroup[] => {
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

export const shortLocation = (label: string, sharedSheet?: string) => {
  if (!sharedSheet || !label.startsWith(`${sharedSheet}!`)) return label
  return label.slice(sharedSheet.length + 1)
}
