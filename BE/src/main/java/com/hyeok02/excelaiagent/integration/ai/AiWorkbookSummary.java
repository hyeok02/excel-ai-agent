package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.model.AiDependencySummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiExcludedSheetSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiSheetSummary;

public record AiWorkbookSummary(
		String filename,
		@JsonProperty("sheet_count") int sheetCount,
		List<AiSheetSummary> sheets,
		@JsonProperty("total_sheet_count") Integer totalSheetCount,
		@JsonProperty("excluded_sheet_count") Integer excludedSheetCount,
		@JsonProperty("excluded_sheets") List<AiExcludedSheetSummary> excludedSheets,
		@JsonProperty("dependency_summary") AiDependencySummary dependencySummary) {

	public AiWorkbookSummary(String filename, int sheetCount, List<AiSheetSummary> sheets) {
		this(filename, sheetCount, sheets, sheetCount, 0, List.of(), null);
	}

	public AiWorkbookSummary(String filename, int sheetCount, List<AiSheetSummary> sheets,
			AiDependencySummary dependencySummary) {
		this(filename, sheetCount, sheets, sheetCount, 0, List.of(), dependencySummary);
	}
}
