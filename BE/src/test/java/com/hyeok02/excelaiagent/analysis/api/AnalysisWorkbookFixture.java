package com.hyeok02.excelaiagent.analysis.api;

import java.util.List;
import com.hyeok02.excelaiagent.integration.ai.*;
import com.hyeok02.excelaiagent.integration.ai.model.*;

final class AnalysisWorkbookFixture {
	private AnalysisWorkbookFixture() {
	}

	static AiWorkbookSummary summary() {
		AiSheetSummary sheet = new AiSheetSummary(
				"Sales", 3, 4, 1, 0, 1,
				List.of(new AiFormulaAnalysis(
						"D2", "=SUM(B2:C2)", List.of("B2:C2"), 15, "calculation",
						provenance("formula_parser", "formula", "D2", "=SUM(B2:C2)"))),
				1, List.of(region()),
				List.of(new AiTableSummary("SalesTable", "SalesTable", "A1:D3",
						List.of("상품", "1월", "2월", "합계"), 3, 4, List.of(), false)),
				List.of(new AiChartSummary("월별 매출", "BarChart", "F2", 1,
						List.of(new AiChartSeriesSummary("1월", "'Sales'!$A$2:$A$3",
								"'Sales'!$B$2:$B$3", List.of("노트북", "모니터"), List.of(10, 5))), false)),
				new AiAnalysisInclusion(AnalysisDecision.INCLUDE, "business_worksheet", "사용자 업무 시트"),
				classification(SheetRole.OUTPUT, SheetImportance.HIGH, 60),
				List.of(new AiColumnSchema(
						"B", "A1:D3", List.of("매출액"), "매출액", "revenue",
						"number", "currency", "KRW", 0.93,
						List.of("헤더 의미어 일치", "통화 표시 형식"),
						provenance("column_schema_analyzer", "range", "A1:D3", null))));
		AiExcludedSheetSummary excluded = new AiExcludedSheetSummary(
				"__snlofficequeries", "visible",
				new AiAnalysisInclusion(AnalysisDecision.EXCLUDE, "addin_cache_worksheet", "애드인 캐시 시트"),
				classification(SheetRole.SYSTEM, SheetImportance.LOW, 0));
		return new AiWorkbookSummary("sales.xlsx", 1, List.of(sheet), 2, 1,
				List.of(excluded), dependency(), formulaRisks());
	}

	static AiWorkbookInsights insights() {
		return new AiWorkbookInsights(summary(), new AiWorkbookInsights.InsightReport(
				"수식 구조를 검토했습니다.",
				List.of(new AiWorkbookInsights.Insight(
						"수식 참조 확인", "Sales 시트의 수식 참조를 확인해야 합니다.",
						"formula", "warning", List.of("Sales!D2"), "참조 범위를 검토하세요.")),
				List.of("실제 셀 값은 분석하지 않았습니다.")));
	}

	private static AiSheetClassification classification(
			SheetRole role, SheetImportance importance, int score) {
		return new AiSheetClassification(role, importance, 0.9, score,
				List.of(new AiSheetRoleReason(
						role == SheetRole.SYSTEM ? "system_policy" : "chart_presentation",
						role == SheetRole.SYSTEM ? "애드인 캐시 시트" : "차트 1개 포함",
						List.of("Sales!D2"))));
	}

	private static AiCellRegion region() {
		AiSemanticClassification data = new AiSemanticClassification(
				SemanticRole.DATA, 0.91,
				List.of(new AiSemanticReason("tabular_values", "헤더 아래 반복 데이터", List.of("Sales!A1:D3"))));
		return new AiCellRegion("A1", "D3", 12, null, 3, 4, List.of(), List.of(),
				List.of(List.of(cell())), false, data);
	}

	private static AiCellSnapshot cell() {
		AiSemanticClassification header = new AiSemanticClassification(
				SemanticRole.HEADER, 0.86,
				List.of(new AiSemanticReason("header_style", "굵은 글꼴과 배경색", List.of("Sales!A1"))));
		return new AiCellSnapshot("A1", "상품", null, null,
				"General", true, null, "center", false, header);
	}

	private static AiDependencySummary dependency() {
		AiDependencyNode range = new AiDependencyNode(
				"Sales!B2:C2", "Sales!B2:C2", "Sales", "B2:C2", "range", null);
		AiDependencyNode formula = new AiDependencyNode(
				"Sales!D2", "Sales!D2", "Sales", "D2", "formula", "=SUM(B2:C2)");
		AiDependencyEdge edge = new AiDependencyEdge("Sales!B2:C2", "Sales!D2", "B2:C2", false);
		AiDependencyCluster cluster = new AiDependencyCluster(
				"cluster-1", 2, 1, 1, List.of("Sales"), List.of(range, formula), List.of(edge), false);
		AiDependencyCycle cycle = new AiDependencyCycle(
				"cycle-1", 1, 1, List.of("Sales"), List.of(formula),
				List.of(new AiDependencyEdge("Sales!D2", "Sales!D2", "D2", false)), false);
		return new AiDependencySummary(2, 1, 1, 0, 0, 0, 1,
				List.of(cluster), 1, 1, List.of(cycle));
	}

	private static AiFormulaRiskSummary formulaRisks() {
		AiFormulaRiskImpact impact = new AiFormulaRiskImpact(
				2, 1, List.of("Dashboard"), 2, 62, "high");
		AiFormulaRiskFinding finding = new AiFormulaRiskFinding(
				"external_reference", "warning", "Sales", "D2",
				"외부 파일의 값을 참조합니다.", "='[Budget.xlsx]Plan'!C3",
				"[Budget.xlsx]Plan!C3", null, null,
				provenance("formula_risk_detector", "formula", "D2", "='[Budget.xlsx]Plan'!C3"),
				impact);
		return new AiFormulaRiskSummary(1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, List.of(finding));
	}

	private static AiProvenance provenance(
			String analyzer, String kind, String reference, String formula) {
		AiAnalysisEvidence evidence = new AiAnalysisEvidence(
				kind, "Sales", reference, "테스트 원본 근거", 15, formula);
		return new AiProvenance(analyzer, "rule_based", 0.93, List.of(evidence));
	}
}
