package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiWorkbookSummary(
		String filename,
		@JsonProperty("sheet_count") int sheetCount,
		List<SheetSummary> sheets) {

	public record SheetSummary(
			String name,
			int rows,
			int columns,
			@JsonProperty("formula_count") int formulaCount,
			@JsonProperty("table_count") int tableCount,
			@JsonProperty("chart_count") int chartCount,
			List<FormulaAnalysis> formulas,
			@JsonProperty("region_count") int regionCount,
			List<CellRegion> regions) {
	}

	public record FormulaAnalysis(
			String cell,
			String formula,
			List<String> references) {
	}

	public record CellRegion(
			@JsonProperty("start_cell") String startCell,
			@JsonProperty("end_cell") String endCell,
			@JsonProperty("cell_count") int cellCount) {
	}
}
