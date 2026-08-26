package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisWorkbookResult {
	private AnalysisWorkbookResult() {
	}

	public record Workbook(
			String filename, int sheetCount, int totalSheetCount, int excludedSheetCount,
			List<ExcludedSheet> excludedSheets, List<Sheet> sheets,
			AnalysisDependencyResult.Graph dependencyGraph) {
	}

	public record ExcludedSheet(
			String name, String state, AnalysisSemanticResult.Inclusion analysisInclusion,
			AnalysisSemanticResult.SheetClassification sheetClassification) {
	}

	public record Sheet(
			String name, int rows, int columns, int formulaCount, int tableCount, int chartCount,
			List<Formula> formulas, int regionCount, List<Region> regions,
			List<ColumnSchema> columnSchemas, List<Table> tables, List<Chart> charts,
			AnalysisSemanticResult.Inclusion analysisInclusion,
			AnalysisSemanticResult.SheetClassification sheetClassification) {
	}

	public record Formula(
			String cell, String formula, List<String> references, Object cachedValue, String role) {
	}

	public record Region(
			String startCell, String endCell, int cellCount, String title,
			int rowCount, int columnCount, List<String> mergedRanges,
			List<HeaderPath> headerPaths, List<List<Cell>> previewRows, boolean truncated,
			AnalysisSemanticResult.Semantic semantic,
			AnalysisSemanticResult.Inclusion analysisInclusion) {
	}

	public record HeaderPath(String column, List<String> labels) {
	}

	public record ColumnSchema(
			String column, String sourceRange, List<String> headerPath, String displayName,
			String standardField, String dataType, String unitType, String unitLabel,
			double confidence, List<String> evidence) {
	}

	public record Cell(
			String address, Object value, String formula, Object cachedValue,
			String numberFormat, boolean bold, String fillColor,
			String horizontalAlignment, boolean merged,
			AnalysisSemanticResult.Semantic semantic) {
	}

	public record Table(
			String name, String displayName, String reference, List<String> headers,
			int rowCount, int columnCount, List<List<Cell>> previewRows, boolean truncated) {
	}

	public record Chart(
			String title, String chartType, String anchorCell, int seriesCount,
			List<ChartSeries> series, boolean truncated) {
	}

	public record ChartSeries(
			String title, String categoriesReference, String valuesReference,
			List<Object> categorySamples, List<Object> valueSamples) {
	}
}
