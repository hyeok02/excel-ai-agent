import type { DependencyClusterResult } from '@/api/analysis'
import type { RelationshipGroup } from '@/components/analysis/result/dependency/dependencyMapUtils'
import {
  groupRelationships,
  parseCellLabel,
} from '@/components/analysis/result/dependency/dependencyMapUtils'
import { describeFormulaMeaning } from '@/components/analysis/result/dependency/formulaMeaning'

export interface RelationshipPattern {
  meaning: string
  relationships: RelationshipGroup[]
}

export interface SheetRelationshipPattern extends RelationshipPattern {
  sheetName: string
}

export const groupClusterPatterns = (
  clusters: DependencyClusterResult[],
): SheetRelationshipPattern[] => {
  const grouped = new Map<string, SheetRelationshipPattern>()

  clusters.flatMap(groupRelationships).forEach((relationship) => {
    const sheetName =
      parseCellLabel(relationship.targetLabel)?.sheet ??
      relationship.target?.sheet ??
      '워크북'
    const meaning = describeFormulaMeaning(relationship.target?.formula ?? null)
    const key = `${sheetName}\u0000${meaning}`
    const pattern = grouped.get(key) ?? { sheetName, meaning, relationships: [] }
    pattern.relationships.push(relationship)
    grouped.set(key, pattern)
  })

  return [...grouped.values()].sort(
    (left, right) => right.relationships.length - left.relationships.length,
  )
}
