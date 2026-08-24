package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiWorkbookSummary(
		String filename,
		@JsonProperty("sheet_count") int sheetCount,
		List<SheetSummary> sheets,
		@JsonProperty("total_sheet_count") Integer totalSheetCount,
		@JsonProperty("excluded_sheet_count") Integer excludedSheetCount,
		@JsonProperty("excluded_sheets") List<ExcludedSheetSummary> excludedSheets,
		@JsonProperty("dependency_summary") DependencySummary dependencySummary) {

	public AiWorkbookSummary(String filename, int sheetCount, List<SheetSummary> sheets) {
		this(filename, sheetCount, sheets, sheetCount, 0, List.of(), null);
	}

	public AiWorkbookSummary(
			String filename,
			int sheetCount,
			List<SheetSummary> sheets,
			DependencySummary dependencySummary) {
		this(filename, sheetCount, sheets, sheetCount, 0, List.of(), dependencySummary);
	}

	public record ExcludedSheetSummary(
			String name,
			String state,
			@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion) {
	}

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
			List<ChartSummary> charts,
			@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion) {

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
					regionCount, regions, List.of(), List.of(), null);
		}

		public SheetSummary(
				String name, int rows, int columns, int formulaCount, int tableCount,
				int chartCount, List<FormulaAnalysis> formulas, int regionCount,
				List<CellRegion> regions, List<TableSummary> tables, List<ChartSummary> charts) {
			this(name, rows, columns, formulaCount, tableCount, chartCount, formulas,
					regionCount, regions, tables, charts, null);
		}
	}

	public record FormulaAnalysis(
			String cell,
			String formula,
			List<String> references,
			@JsonProperty("cached_value") Object cachedValue,
			String role) {

		public FormulaAnalysis(String cell, String formula, List<String> references) {
			this(cell, formula, references, null, "calculation");
		}
	}

	public record CellRegion(
			@JsonProperty("start_cell") String startCell,
			@JsonProperty("end_cell") String endCell,
			@JsonProperty("cell_count") int cellCount,
			String title,
			@JsonProperty("row_count") Integer rowCount,
			@JsonProperty("column_count") Integer columnCount,
			@JsonProperty("merged_ranges") List<String> mergedRanges,
			@JsonProperty("header_paths") List<HeaderPath> headerPaths,
			@JsonProperty("preview_rows") List<List<CellSnapshot>> previewRows,
			@JsonProperty("is_truncated") Boolean truncated,
			AiSemanticClassification semantic,
			@JsonProperty("analysis_inclusion") AiAnalysisInclusion analysisInclusion) {

		public CellRegion(
				String startCell,
				String endCell,
				int cellCount,
				String title,
				Integer rowCount,
				Integer columnCount,
				List<String> mergedRanges,
				List<HeaderPath> headerPaths,
				List<List<CellSnapshot>> previewRows,
				Boolean truncated) {
			this(startCell, endCell, cellCount, title, rowCount, columnCount,
					mergedRanges, headerPaths, previewRows, truncated, null, null);
		}

		public CellRegion(
				String startCell, String endCell, int cellCount, String title,
				Integer rowCount, Integer columnCount, List<String> mergedRanges,
				List<HeaderPath> headerPaths, List<List<CellSnapshot>> previewRows,
				Boolean truncated, AiSemanticClassification semantic) {
			this(startCell, endCell, cellCount, title, rowCount, columnCount,
					mergedRanges, headerPaths, previewRows, truncated, semantic, null);
		}

		public CellRegion(String startCell, String endCell, int cellCount) {
			this(startCell, endCell, cellCount, null, 0, 0, List.of(), List.of(), List.of(), false);
		}

		public CellRegion(
				String startCell,
				String endCell,
				int cellCount,
				List<List<CellSnapshot>> previewRows,
				Boolean truncated) {
			this(startCell, endCell, cellCount, null, 0, 0, List.of(), List.of(), previewRows, truncated);
		}
	}

	public record HeaderPath(
			String column,
			List<String> labels) {
	}

	public record CellSnapshot(
			String address,
			Object value,
			String formula,
			@JsonProperty("cached_value") Object cachedValue,
			@JsonProperty("number_format") String numberFormat,
			Boolean bold,
			@JsonProperty("fill_color") String fillColor,
			@JsonProperty("horizontal_alignment") String horizontalAlignment,
			Boolean merged,
			AiSemanticClassification semantic) {

		public CellSnapshot(
				String address,
				Object value,
				String formula,
				Object cachedValue,
				String numberFormat,
				Boolean bold,
				String fillColor,
				String horizontalAlignment,
				Boolean merged) {
			this(address, value, formula, cachedValue, numberFormat, bold,
					fillColor, horizontalAlignment, merged, null);
		}

		public CellSnapshot(String address, Object value, String formula) {
			this(address, value, formula, null, null, false, null, null, false);
		}
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

	public record DependencySummary(
			@JsonProperty("node_count") int nodeCount,
			@JsonProperty("edge_count") int edgeCount,
			@JsonProperty("formula_node_count") int formulaNodeCount,
			@JsonProperty("cross_sheet_edge_count") int crossSheetEdgeCount,
			@JsonProperty("named_reference_count") int namedReferenceCount,
			@JsonProperty("external_reference_count") int externalReferenceCount,
			@JsonProperty("cluster_count") int clusterCount,
			List<DependencyCluster> clusters,
			@JsonProperty("cycle_count") int cycleCount,
			@JsonProperty("cyclic_node_count") int cyclicNodeCount,
			List<DependencyCycle> cycles) {
	}

	public record DependencyCluster(
			String id,
			@JsonProperty("node_count") int nodeCount,
			@JsonProperty("edge_count") int edgeCount,
			@JsonProperty("formula_count") int formulaCount,
			@JsonProperty("sheet_names") List<String> sheetNames,
			List<DependencyNode> nodes,
			List<DependencyEdge> edges,
			@JsonProperty("is_truncated") Boolean truncated) {
	}

	public record DependencyCycle(
			String id,
			@JsonProperty("node_count") int nodeCount,
			@JsonProperty("edge_count") int edgeCount,
			@JsonProperty("sheet_names") List<String> sheetNames,
			List<DependencyNode> nodes,
			List<DependencyEdge> edges,
			@JsonProperty("is_truncated") Boolean truncated) {
	}

	public record DependencyNode(
			String id,
			String label,
			String sheet,
			String cell,
			String kind,
			String formula) {
	}

	public record DependencyEdge(
			String source,
			String target,
			String reference,
			@JsonProperty("cross_sheet") boolean crossSheet) {
	}
}
