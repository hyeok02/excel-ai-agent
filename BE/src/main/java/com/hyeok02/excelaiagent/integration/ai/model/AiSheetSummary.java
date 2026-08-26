package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.AiAnalysisInclusion;
import com.hyeok02.excelaiagent.integration.ai.AiSheetClassification;

public record AiSheetSummary(
		String name, int rows, int columns,
		@JsonProperty("formula_count") int formulaCount,
		@JsonProperty("table_count") int tableCount,
		@JsonProperty("chart_count") int chartCount,
		List<AiFormulaAnalysis> formulas,
		@JsonProperty("region_count") int regionCount,
		List<AiCellRegion> regions, List<AiTableSummary> tables,
		List<AiChartSummary> charts,
		@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion,
		@JsonProperty("sheet_classification") AiSheetClassification sheetClassification,
		@JsonProperty("column_schemas") List<AiColumnSchema> columnSchemas) {
	public AiSheetSummary(String name, int rows, int columns, int formulasCount,
			int tablesCount, int chartsCount, List<AiFormulaAnalysis> formulas,
			int regionsCount, List<AiCellRegion> regions, List<AiTableSummary> tables,
			List<AiChartSummary> charts, AiAnalysisInclusion inclusion,
			AiSheetClassification classification) {
		this(name, rows, columns, formulasCount, tablesCount, chartsCount, formulas,
				regionsCount, regions, tables, charts, inclusion, classification, List.of());
	}
	public AiSheetSummary(String name, int rows, int columns, int formulasCount,
			int tablesCount, int chartsCount, List<AiFormulaAnalysis> formulas,
			int regionsCount, List<AiCellRegion> regions) {
		this(name, rows, columns, formulasCount, tablesCount, chartsCount, formulas,
				regionsCount, regions, List.of(), List.of(), null, null, List.of());
	}
	public AiSheetSummary(String name, int rows, int columns, int formulasCount,
			int tablesCount, int chartsCount, List<AiFormulaAnalysis> formulas,
			int regionsCount, List<AiCellRegion> regions, List<AiTableSummary> tables,
			List<AiChartSummary> charts) {
		this(name, rows, columns, formulasCount, tablesCount, chartsCount, formulas,
				regionsCount, regions, tables, charts, null, null, List.of());
	}
	public AiSheetSummary(String name, int rows, int columns, int formulasCount,
			int tablesCount, int chartsCount, List<AiFormulaAnalysis> formulas,
			int regionsCount, List<AiCellRegion> regions, List<AiTableSummary> tables,
			List<AiChartSummary> charts, AiAnalysisInclusion inclusion) {
		this(name, rows, columns, formulasCount, tablesCount, chartsCount, formulas,
				regionsCount, regions, tables, charts, inclusion, null, List.of());
	}
}
