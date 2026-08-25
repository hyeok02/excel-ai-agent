package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiCellRegion;
import com.hyeok02.excelaiagent.integration.ai.model.AiCellSnapshot;
import com.hyeok02.excelaiagent.integration.ai.model.AiChartSeriesSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiChartSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiExcludedSheetSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiFormulaAnalysis;
import com.hyeok02.excelaiagent.integration.ai.model.AiHeaderPath;
import com.hyeok02.excelaiagent.integration.ai.model.AiSheetSummary;
import com.hyeok02.excelaiagent.integration.ai.model.AiTableSummary;

final class WorkbookResultMapper {
	private WorkbookResultMapper() {
	}

	static AnalysisWorkbookResult.Workbook map(AiWorkbookSummary workbook) {
		int totalSheets = workbook.totalSheetCount() != null && workbook.totalSheetCount() > 0
				? workbook.totalSheetCount() : workbook.sheetCount();
		return new AnalysisWorkbookResult.Workbook(
				workbook.filename(), workbook.sheetCount(), totalSheets,
				workbook.excludedSheetCount() == null ? 0 : workbook.excludedSheetCount(),
				SemanticResultMapper.safe(workbook.excludedSheets()).stream()
						.map(WorkbookResultMapper::map).toList(),
				SemanticResultMapper.safe(workbook.sheets()).stream()
						.map(WorkbookResultMapper::map).toList(),
				DependencyResultMapper.map(workbook.dependencySummary()));
	}

	private static AnalysisWorkbookResult.ExcludedSheet map(AiExcludedSheetSummary sheet) {
		return new AnalysisWorkbookResult.ExcludedSheet(
				sheet.name(), sheet.state(), SemanticResultMapper.map(sheet.analysisInclusion()),
				SemanticResultMapper.map(sheet.sheetClassification()));
	}

	private static AnalysisWorkbookResult.Sheet map(AiSheetSummary sheet) {
		return new AnalysisWorkbookResult.Sheet(
				sheet.name(), sheet.rows(), sheet.columns(), sheet.formulaCount(),
				sheet.tableCount(), sheet.chartCount(),
				SemanticResultMapper.safe(sheet.formulas()).stream().map(WorkbookResultMapper::map).toList(),
				sheet.regionCount(),
				SemanticResultMapper.safe(sheet.regions()).stream().map(WorkbookResultMapper::map).toList(),
				SemanticResultMapper.safe(sheet.tables()).stream().map(WorkbookResultMapper::map).toList(),
				SemanticResultMapper.safe(sheet.charts()).stream().map(WorkbookResultMapper::map).toList(),
				SemanticResultMapper.map(sheet.analysisInclusion()),
				SemanticResultMapper.map(sheet.sheetClassification()));
	}

	private static AnalysisWorkbookResult.Formula map(AiFormulaAnalysis formula) {
		return new AnalysisWorkbookResult.Formula(
				formula.cell(), formula.formula(), formula.references(),
				formula.cachedValue(), formula.role());
	}

	private static AnalysisWorkbookResult.Region map(AiCellRegion region) {
		return new AnalysisWorkbookResult.Region(
				region.startCell(), region.endCell(), region.cellCount(), region.title(),
				region.rowCount() == null ? 0 : region.rowCount(),
				region.columnCount() == null ? 0 : region.columnCount(),
				SemanticResultMapper.safe(region.mergedRanges()),
				SemanticResultMapper.safe(region.headerPaths()).stream().map(WorkbookResultMapper::map).toList(),
				mapRows(region.previewRows()), Boolean.TRUE.equals(region.truncated()),
				SemanticResultMapper.map(region.semantic()),
				SemanticResultMapper.map(region.analysisInclusion()));
	}

	private static AnalysisWorkbookResult.HeaderPath map(AiHeaderPath header) {
		return new AnalysisWorkbookResult.HeaderPath(header.column(), SemanticResultMapper.safe(header.labels()));
	}

	private static AnalysisWorkbookResult.Cell map(AiCellSnapshot cell) {
		return new AnalysisWorkbookResult.Cell(
				cell.address(), cell.value(), cell.formula(), cell.cachedValue(),
				cell.numberFormat(), Boolean.TRUE.equals(cell.bold()), cell.fillColor(),
				cell.horizontalAlignment(), Boolean.TRUE.equals(cell.merged()),
				SemanticResultMapper.map(cell.semantic()));
	}

	private static AnalysisWorkbookResult.Table map(AiTableSummary table) {
		return new AnalysisWorkbookResult.Table(
				table.name(), table.displayName(), table.reference(),
				SemanticResultMapper.safe(table.headers()), table.rowCount(), table.columnCount(),
				mapRows(table.previewRows()), Boolean.TRUE.equals(table.truncated()));
	}

	private static AnalysisWorkbookResult.Chart map(AiChartSummary chart) {
		return new AnalysisWorkbookResult.Chart(
				chart.title(), chart.chartType(), chart.anchorCell(), chart.seriesCount(),
				SemanticResultMapper.safe(chart.series()).stream().map(WorkbookResultMapper::map).toList(),
				Boolean.TRUE.equals(chart.truncated()));
	}

	private static AnalysisWorkbookResult.ChartSeries map(AiChartSeriesSummary series) {
		return new AnalysisWorkbookResult.ChartSeries(
				series.title(), series.categoriesReference(), series.valuesReference(),
				SemanticResultMapper.safe(series.categorySamples()),
				SemanticResultMapper.safe(series.valueSamples()));
	}

	private static List<List<AnalysisWorkbookResult.Cell>> mapRows(List<List<AiCellSnapshot>> rows) {
		return SemanticResultMapper.safe(rows).stream()
				.map(row -> SemanticResultMapper.safe(row).stream().map(WorkbookResultMapper::map).toList())
				.toList();
	}
}
