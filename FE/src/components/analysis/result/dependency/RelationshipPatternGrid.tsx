import ResponsiveCardColumns from '@/components/analysis/common/ResponsiveCardColumns'
import RelationshipPatternCard from '@/components/analysis/result/dependency/RelationshipPatternCard'
import type { SheetRelationshipPattern } from '@/components/analysis/result/dependency/relationshipPatterns'

interface RelationshipPatternGridProps {
  patterns: SheetRelationshipPattern[]
}

const RelationshipPatternGrid = ({ patterns }: RelationshipPatternGridProps) => (
  <ResponsiveCardColumns
    breakpoint="xl"
    getKey={(pattern) => `${pattern.sheetName}-${pattern.meaning}`}
    items={patterns}
    renderItem={(pattern) => (
      <RelationshipPatternCard pattern={pattern} sheetName={pattern.sheetName} />
    )}
  />
)

export default RelationshipPatternGrid
