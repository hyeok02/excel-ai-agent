package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;

public record AnalysisResultDetails(
		UUID analysisId,
		Instant createdAt,
		WorkbookResult workbook,
		InsightReportResult insightReport) {

	public static AnalysisResultDetails from(
			UUID analysisId,
			Instant createdAt,
			AiWorkbookInsights workbookAnalysis) {
		AiWorkbookSummary workbookSummary = workbookAnalysis.workbook();
		return new AnalysisResultDetails(
				analysisId,
				createdAt,
				new WorkbookResult(
						workbookSummary.filename(),
						workbookSummary.sheetCount(),
						workbookSummary.sheets().stream().map(SheetResult::from).toList()),
				InsightReportResult.from(workbookAnalysis.report()));
	}

	public record InsightReportResult(
			String overview,
			List<InsightResult> insights,
			List<String> limitations) {

		private static InsightReportResult from(AiWorkbookInsights.InsightReport report) {
			if (report == null) {
				return null;
			}
			return new InsightReportResult(
					report.overview(),
					report.insights().stream().map(InsightResult::from).toList(),
					report.limitations());
		}
	}

	public record InsightResult(
			String title,
			String description,
			String category,
			String severity,
			List<String> evidence,
			String recommendation) {

		private static InsightResult from(AiWorkbookInsights.Insight insight) {
			return new InsightResult(
					insight.title(),
					insight.description(),
					insight.category(),
					insight.severity(),
					insight.evidence(),
					insight.recommendation());
		}
	}

	public record WorkbookResult(
			String filename,
			int sheetCount,
			List<SheetResult> sheets) {
	}

	public record SheetResult(
			String name,
			int rows,
			int columns,
			int formulaCount,
			int tableCount,
			int chartCount,
			List<FormulaResult> formulas,
			int regionCount,
			List<RegionResult> regions,
			List<TableResult> tables,
			List<ChartResult> charts) {

		private static SheetResult from(AiWorkbookSummary.SheetSummary sheet) {
			return new SheetResult(
					sheet.name(),
					sheet.rows(),
					sheet.columns(),
					sheet.formulaCount(),
					sheet.tableCount(),
					sheet.chartCount(),
					safeList(sheet.formulas()).stream().map(FormulaResult::from).toList(),
					sheet.regionCount(),
					safeList(sheet.regions()).stream().map(RegionResult::from).toList(),
					safeList(sheet.tables()).stream().map(TableResult::from).toList(),
					safeList(sheet.charts()).stream().map(ChartResult::from).toList());
		}
	}

	public record FormulaResult(
			String cell,
			String formula,
			List<String> references) {

		private static FormulaResult from(AiWorkbookSummary.FormulaAnalysis formula) {
			return new FormulaResult(formula.cell(), formula.formula(), formula.references());
		}
	}

	public record RegionResult(
			String startCell,
			String endCell,
			int cellCount,
			List<List<CellResult>> previewRows,
			boolean truncated) {

		private static RegionResult from(AiWorkbookSummary.CellRegion region) {
			return new RegionResult(
					region.startCell(),
					region.endCell(),
					region.cellCount(),
					cellRows(region.previewRows()),
					Boolean.TRUE.equals(region.truncated()));
		}
	}

	public record CellResult(
			String address,
			Object value,
			String formula) {

		private static CellResult from(AiWorkbookSummary.CellSnapshot cell) {
			return new CellResult(cell.address(), cell.value(), cell.formula());
		}
	}

	public record TableResult(
			String name,
			String displayName,
			String reference,
			List<String> headers,
			int rowCount,
			int columnCount,
			List<List<CellResult>> previewRows,
			boolean truncated) {

		private static TableResult from(AiWorkbookSummary.TableSummary table) {
			return new TableResult(
					table.name(),
					table.displayName(),
					table.reference(),
					safeList(table.headers()),
					table.rowCount(),
					table.columnCount(),
					cellRows(table.previewRows()),
					Boolean.TRUE.equals(table.truncated()));
		}
	}

	public record ChartResult(
			String title,
			String chartType,
			String anchorCell,
			int seriesCount,
			List<ChartSeriesResult> series,
			boolean truncated) {

		private static ChartResult from(AiWorkbookSummary.ChartSummary chart) {
			return new ChartResult(
					chart.title(),
					chart.chartType(),
					chart.anchorCell(),
					chart.seriesCount(),
					safeList(chart.series()).stream().map(ChartSeriesResult::from).toList(),
					Boolean.TRUE.equals(chart.truncated()));
		}
	}

	public record ChartSeriesResult(
			String title,
			String categoriesReference,
			String valuesReference,
			List<Object> categorySamples,
			List<Object> valueSamples) {

		private static ChartSeriesResult from(AiWorkbookSummary.ChartSeriesSummary series) {
			return new ChartSeriesResult(
					series.title(),
					series.categoriesReference(),
					series.valuesReference(),
					safeList(series.categorySamples()),
					safeList(series.valueSamples()));
		}
	}

	private static List<List<CellResult>> cellRows(List<List<AiWorkbookSummary.CellSnapshot>> rows) {
		return safeList(rows).stream()
				.map(row -> safeList(row).stream().map(CellResult::from).toList())
				.toList();
	}

	private static <T> List<T> safeList(List<T> values) {
		return values == null ? List.of() : values;
	}
}
