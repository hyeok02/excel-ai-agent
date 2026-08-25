import { useMemo } from 'react'

import type { SemanticRole, SheetResult } from '@/api/analysis'
import {
  getSheetSemanticMetadata,
  type SemanticSheetRole,
} from '@/components/analysis/workbook/semantic/semanticModel'

export const useSemanticOverview = (sheets: SheetResult[]) =>
  useMemo(() => {
    const regionCounts = new Map<SemanticRole, number>()
    const sheetCounts = new Map<SemanticSheetRole, number>()
    let classifiedRegionCount = 0

    sheets.forEach((sheet) => {
      const { classification } = getSheetSemanticMetadata(sheet)
      if (classification) {
        sheetCounts.set(
          classification.role,
          (sheetCounts.get(classification.role) ?? 0) + 1,
        )
      }

      for (const region of sheet.regions ?? []) {
        if (!region.semantic) continue
        classifiedRegionCount += 1
        regionCounts.set(
          region.semantic.role,
          (regionCounts.get(region.semantic.role) ?? 0) + 1,
        )
      }
    })

    return {
      classifiedRegionCount,
      regionRoleCounts: [...regionCounts.entries()].sort(
        (left, right) => right[1] - left[1],
      ),
      sheetRoleCounts: [...sheetCounts.entries()],
    }
  }, [sheets])
