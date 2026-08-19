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
			List<RegionResult> regions) {

		private static SheetResult from(AiWorkbookSummary.SheetSummary sheet) {
			return new SheetResult(
					sheet.name(),
					sheet.rows(),
					sheet.columns(),
					sheet.formulaCount(),
					sheet.tableCount(),
					sheet.chartCount(),
					sheet.formulas().stream().map(FormulaResult::from).toList(),
					sheet.regionCount(),
					sheet.regions().stream().map(RegionResult::from).toList());
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
			int cellCount) {

		private static RegionResult from(AiWorkbookSummary.CellRegion region) {
			return new RegionResult(region.startCell(), region.endCell(), region.cellCount());
		}
	}
}
