package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import com.hyeok02.excelaiagent.integration.ai.AiAnalysisInclusion;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticClassification;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticReason;

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
						workbookSummary.totalSheetCount() != null && workbookSummary.totalSheetCount() > 0
								? workbookSummary.totalSheetCount()
								: workbookSummary.sheetCount(),
						workbookSummary.excludedSheetCount() == null
								? 0
								: workbookSummary.excludedSheetCount(),
						safeList(workbookSummary.excludedSheets()).stream()
								.map(ExcludedSheetResult::from)
								.toList(),
						workbookSummary.sheets().stream().map(SheetResult::from).toList(),
						DependencyResult.from(workbookSummary.dependencySummary())),
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
			int totalSheetCount,
			int excludedSheetCount,
			List<ExcludedSheetResult> excludedSheets,
			List<SheetResult> sheets,
			DependencyResult dependencyGraph) {
	}

	public record ExcludedSheetResult(
			String name,
			String state,
			AnalysisInclusionResult analysisInclusion) {

		private static ExcludedSheetResult from(AiWorkbookSummary.ExcludedSheetSummary sheet) {
			return new ExcludedSheetResult(
					sheet.name(),
					sheet.state(),
					AnalysisInclusionResult.from(sheet.analysisInclusion()));
		}
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
			List<ChartResult> charts,
			AnalysisInclusionResult analysisInclusion) {

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
					safeList(sheet.charts()).stream().map(ChartResult::from).toList(),
					AnalysisInclusionResult.from(sheet.analysisInclusion()));
		}
	}

	public record FormulaResult(
			String cell,
			String formula,
			List<String> references,
			Object cachedValue,
			String role) {

		private static FormulaResult from(AiWorkbookSummary.FormulaAnalysis formula) {
			return new FormulaResult(
					formula.cell(),
					formula.formula(),
					formula.references(),
					formula.cachedValue(),
					formula.role());
		}
	}

	public record RegionResult(
			String startCell,
			String endCell,
			int cellCount,
			String title,
			int rowCount,
			int columnCount,
			List<String> mergedRanges,
			List<HeaderPathResult> headerPaths,
			List<List<CellResult>> previewRows,
			boolean truncated,
			SemanticClassificationResult semantic,
			AnalysisInclusionResult analysisInclusion) {

		private static RegionResult from(AiWorkbookSummary.CellRegion region) {
			return new RegionResult(
					region.startCell(),
					region.endCell(),
					region.cellCount(),
					region.title(),
					region.rowCount() == null ? 0 : region.rowCount(),
					region.columnCount() == null ? 0 : region.columnCount(),
					safeList(region.mergedRanges()),
					safeList(region.headerPaths()).stream().map(HeaderPathResult::from).toList(),
					cellRows(region.previewRows()),
					Boolean.TRUE.equals(region.truncated()),
					SemanticClassificationResult.from(region.semantic()),
					AnalysisInclusionResult.from(region.analysisInclusion()));
		}
	}

	public record AnalysisInclusionResult(
			String decision,
			String reasonCode,
			String reason) {

		private static AnalysisInclusionResult from(AiAnalysisInclusion inclusion) {
			if (inclusion == null) {
				return null;
			}
			return new AnalysisInclusionResult(
					inclusion.decision().value(),
					inclusion.reasonCode(),
					inclusion.reason());
		}
	}

	public record HeaderPathResult(
			String column,
			List<String> labels) {

		private static HeaderPathResult from(AiWorkbookSummary.HeaderPath headerPath) {
			return new HeaderPathResult(headerPath.column(), safeList(headerPath.labels()));
		}
	}

	public record CellResult(
			String address,
			Object value,
			String formula,
			Object cachedValue,
			String numberFormat,
			boolean bold,
			String fillColor,
			String horizontalAlignment,
			boolean merged,
			SemanticClassificationResult semantic) {

		private static CellResult from(AiWorkbookSummary.CellSnapshot cell) {
			return new CellResult(
					cell.address(),
					cell.value(),
					cell.formula(),
					cell.cachedValue(),
					cell.numberFormat(),
					Boolean.TRUE.equals(cell.bold()),
					cell.fillColor(),
					cell.horizontalAlignment(),
					Boolean.TRUE.equals(cell.merged()),
					SemanticClassificationResult.from(cell.semantic()));
		}
	}

	public record SemanticClassificationResult(
			String role,
			double confidence,
			List<SemanticReasonResult> reasons) {

		private static SemanticClassificationResult from(AiSemanticClassification semantic) {
			if (semantic == null) {
				return null;
			}
			return new SemanticClassificationResult(
					semantic.role().value(),
					semantic.confidence(),
					safeList(semantic.reasons()).stream().map(SemanticReasonResult::from).toList());
		}
	}

	public record SemanticReasonResult(
			String code,
			String message,
			List<String> evidenceCells) {

		private static SemanticReasonResult from(
				AiSemanticReason reason) {
			return new SemanticReasonResult(
					reason.code(),
					reason.message(),
					safeList(reason.evidenceCells()));
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

	public record DependencyResult(
			int nodeCount,
			int edgeCount,
			int formulaNodeCount,
			int crossSheetEdgeCount,
			int namedReferenceCount,
			int externalReferenceCount,
			int clusterCount,
			List<DependencyClusterResult> clusters,
			int cycleCount,
			int cyclicNodeCount,
			List<DependencyCycleResult> cycles) {

		private static DependencyResult from(AiWorkbookSummary.DependencySummary summary) {
			if (summary == null) {
				return new DependencyResult(0, 0, 0, 0, 0, 0, 0, List.of(), 0, 0, List.of());
			}
			return new DependencyResult(
					summary.nodeCount(),
					summary.edgeCount(),
					summary.formulaNodeCount(),
					summary.crossSheetEdgeCount(),
					summary.namedReferenceCount(),
					summary.externalReferenceCount(),
					summary.clusterCount(),
					safeList(summary.clusters()).stream()
							.map(DependencyClusterResult::from)
							.toList(),
					summary.cycleCount(),
					summary.cyclicNodeCount(),
					safeList(summary.cycles()).stream()
							.map(DependencyCycleResult::from)
							.toList());
		}
	}

	public record DependencyClusterResult(
			String id,
			int nodeCount,
			int edgeCount,
			int formulaCount,
			List<String> sheetNames,
			List<DependencyNodeResult> nodes,
			List<DependencyEdgeResult> edges,
			boolean truncated) {

		private static DependencyClusterResult from(AiWorkbookSummary.DependencyCluster cluster) {
			return new DependencyClusterResult(
					cluster.id(),
					cluster.nodeCount(),
					cluster.edgeCount(),
					cluster.formulaCount(),
					safeList(cluster.sheetNames()),
					safeList(cluster.nodes()).stream().map(DependencyNodeResult::from).toList(),
					safeList(cluster.edges()).stream().map(DependencyEdgeResult::from).toList(),
					Boolean.TRUE.equals(cluster.truncated()));
		}
	}

	public record DependencyCycleResult(
			String id,
			int nodeCount,
			int edgeCount,
			List<String> sheetNames,
			List<DependencyNodeResult> nodes,
			List<DependencyEdgeResult> edges,
			boolean truncated) {

		private static DependencyCycleResult from(AiWorkbookSummary.DependencyCycle cycle) {
			return new DependencyCycleResult(
					cycle.id(),
					cycle.nodeCount(),
					cycle.edgeCount(),
					safeList(cycle.sheetNames()),
					safeList(cycle.nodes()).stream().map(DependencyNodeResult::from).toList(),
					safeList(cycle.edges()).stream().map(DependencyEdgeResult::from).toList(),
					Boolean.TRUE.equals(cycle.truncated()));
		}
	}

	public record DependencyNodeResult(
			String id,
			String label,
			String sheet,
			String cell,
			String kind,
			String formula) {

		private static DependencyNodeResult from(AiWorkbookSummary.DependencyNode node) {
			return new DependencyNodeResult(
					node.id(), node.label(), node.sheet(), node.cell(), node.kind(), node.formula());
		}
	}

	public record DependencyEdgeResult(
			String source,
			String target,
			String reference,
			boolean crossSheet) {

		private static DependencyEdgeResult from(AiWorkbookSummary.DependencyEdge edge) {
			return new DependencyEdgeResult(
					edge.source(), edge.target(), edge.reference(), edge.crossSheet());
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
