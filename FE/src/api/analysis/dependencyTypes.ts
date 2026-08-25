export type DependencyNodeKind = 'formula' | 'cell' | 'range' | 'named' | 'external'

export interface DependencyNodeResult {
  id: string
  label: string
  sheet: string | null
  cell: string | null
  kind: DependencyNodeKind
  formula: string | null
}

export interface DependencyEdgeResult {
  source: string
  target: string
  reference: string
  crossSheet: boolean
}

export interface DependencyClusterResult {
  id: string
  nodeCount: number
  edgeCount: number
  formulaCount: number
  sheetNames: string[]
  nodes: DependencyNodeResult[]
  edges: DependencyEdgeResult[]
  truncated: boolean
}

export interface DependencyCycleResult {
  id: string
  nodeCount: number
  edgeCount: number
  sheetNames: string[]
  nodes: DependencyNodeResult[]
  edges: DependencyEdgeResult[]
  truncated: boolean
}

export interface DependencyGraphResult {
  nodeCount: number
  edgeCount: number
  formulaNodeCount: number
  crossSheetEdgeCount: number
  namedReferenceCount: number
  externalReferenceCount: number
  clusterCount: number
  clusters: DependencyClusterResult[]
  cycleCount: number
  cyclicNodeCount: number
  cycles: DependencyCycleResult[]
}
