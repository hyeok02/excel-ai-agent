import RelationshipPatternCard from '@/components/analysis/result/dependency/RelationshipPatternCard'
import type { SheetRelationshipPattern } from '@/components/analysis/result/dependency/relationshipPatterns'

interface RelationshipPatternGridProps {
  patterns: SheetRelationshipPattern[]
}

const renderCard = (pattern: SheetRelationshipPattern) => (
  <RelationshipPatternCard
    key={`${pattern.sheetName}-${pattern.meaning}`}
    pattern={pattern}
    sheetName={pattern.sheetName}
  />
)

const RelationshipPatternGrid = ({ patterns }: RelationshipPatternGridProps) => {
  const leftPatterns = patterns.filter((_, index) => index % 2 === 0)
  const rightPatterns = patterns.filter((_, index) => index % 2 === 1)

  return (
    <>
      <div className="space-y-3 xl:hidden">{patterns.map(renderCard)}</div>
      <div className="hidden items-start gap-3 xl:grid xl:grid-cols-2">
        <div className="space-y-3">{leftPatterns.map(renderCard)}</div>
        <div className="space-y-3">{rightPatterns.map(renderCard)}</div>
      </div>
    </>
  )
}

export default RelationshipPatternGrid
