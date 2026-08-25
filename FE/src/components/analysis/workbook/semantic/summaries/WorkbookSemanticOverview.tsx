import type { ExcludedSheetResult, SheetResult } from '@/api/analysis'
import ExcludedSheetsPanel from '@/components/analysis/workbook/semantic/overview/ExcludedSheetsPanel'
import SemanticOverviewHeader from '@/components/analysis/workbook/semantic/overview/SemanticOverviewHeader'
import SemanticOverviewMetrics from '@/components/analysis/workbook/semantic/overview/SemanticOverviewMetrics'
import SemanticRoleDistribution from '@/components/analysis/workbook/semantic/overview/SemanticRoleDistribution'
import { useSemanticOverview } from '@/components/analysis/workbook/semantic/overview/useSemanticOverview'

interface WorkbookSemanticOverviewProps {
  excludedSheets: ExcludedSheetResult[]
  sheets: SheetResult[]
}

const WorkbookSemanticOverview = ({
  excludedSheets,
  sheets,
}: WorkbookSemanticOverviewProps) => {
  const summary = useSemanticOverview(sheets)

  return (
    <section className="mt-6 overflow-hidden rounded-3xl border border-brand-100 bg-white">
      <SemanticOverviewHeader />
      <SemanticOverviewMetrics
        classifiedRegionCount={summary.classifiedRegionCount}
        excludedSheetCount={excludedSheets.length}
        includedSheetCount={sheets.length}
      />
      <SemanticRoleDistribution
        regionRoleCounts={summary.regionRoleCounts}
        sheetRoleCounts={summary.sheetRoleCounts}
      />
      <ExcludedSheetsPanel sheets={excludedSheets} />
    </section>
  )
}

export default WorkbookSemanticOverview
