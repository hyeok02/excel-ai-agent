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
			List<CellRegion> regions,
			List<TableSummary> tables,
			List<ChartSummary> charts) {

		public SheetSummary(
				String name,
				int rows,
				int columns,
				int formulaCount,
				int tableCount,
				int chartCount,
				List<FormulaAnalysis> formulas,
				int regionCount,
				List<CellRegion> regions) {
			this(name, rows, columns, formulaCount, tableCount, chartCount, formulas,
					regionCount, regions, List.of(), List.of());
		}
	}

	public record FormulaAnalysis(
			String cell,
			String formula,
			List<String> references) {
	}

	public record CellRegion(
			@JsonProperty("start_cell") String startCell,
			@JsonProperty("end_cell") String endCell,
			@JsonProperty("cell_count") int cellCount,
			@JsonProperty("preview_rows") List<List<CellSnapshot>> previewRows,
			@JsonProperty("is_truncated") Boolean truncated) {

		public CellRegion(String startCell, String endCell, int cellCount) {
			this(startCell, endCell, cellCount, List.of(), false);
		}
	}

	public record CellSnapshot(
			String address,
			Object value,
			String formula) {
	}

	public record TableSummary(
			String name,
			@JsonProperty("display_name") String displayName,
			String reference,
			List<String> headers,
			@JsonProperty("row_count") int rowCount,
			@JsonProperty("column_count") int columnCount,
			@JsonProperty("preview_rows") List<List<CellSnapshot>> previewRows,
			@JsonProperty("is_truncated") Boolean truncated) {
	}

	public record ChartSummary(
			String title,
			@JsonProperty("chart_type") String chartType,
			@JsonProperty("anchor_cell") String anchorCell,
			@JsonProperty("series_count") int seriesCount,
			List<ChartSeriesSummary> series,
			@JsonProperty("is_truncated") Boolean truncated) {
	}

	public record ChartSeriesSummary(
			String title,
			@JsonProperty("categories_reference") String categoriesReference,
			@JsonProperty("values_reference") String valuesReference,
			@JsonProperty("category_samples") List<Object> categorySamples,
			@JsonProperty("value_samples") List<Object> valueSamples) {
	}
}
