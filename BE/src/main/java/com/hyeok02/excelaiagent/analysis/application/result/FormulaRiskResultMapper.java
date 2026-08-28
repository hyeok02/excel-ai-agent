package com.hyeok02.excelaiagent.analysis.application.result;

import com.hyeok02.excelaiagent.integration.ai.model.AiFormulaRiskFinding;
import com.hyeok02.excelaiagent.integration.ai.model.AiFormulaRiskSummary;

final class FormulaRiskResultMapper {
	private FormulaRiskResultMapper() {
	}

	static AnalysisFormulaRiskResult.Summary map(AiFormulaRiskSummary summary) {
		if (summary == null) {
			return new AnalysisFormulaRiskResult.Summary(
					0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, java.util.List.of());
		}
		return new AnalysisFormulaRiskResult.Summary(
				summary.totalCount(), summary.errorCount(), summary.warningCount(),
				summary.brokenReferenceCount(), summary.missingSheetCount(),
				summary.externalReferenceCount(), summary.dynamicFunctionCount(),
				summary.patternMismatchCount(), summary.hardcodedValueCount(),
				summary.highRiskCount(), summary.criticalRiskCount(),
				summary.findings().stream().map(FormulaRiskResultMapper::map).toList());
	}

	private static AnalysisFormulaRiskResult.Finding map(AiFormulaRiskFinding finding) {
		return new AnalysisFormulaRiskResult.Finding(
				finding.kind(), finding.severity(), finding.sheetName(), finding.cell(),
				finding.message(), finding.formula(), finding.reference(),
				finding.functionName(), finding.observedValue(),
				ProvenanceResultMapper.map(finding.provenance()), map(finding.impact()));
	}

	private static AnalysisFormulaRiskResult.Impact map(
			com.hyeok02.excelaiagent.integration.ai.model.AiFormulaRiskImpact impact) {
		if (impact == null) {
			return null;
		}
		return new AnalysisFormulaRiskResult.Impact(
				impact.affectedFormulaCount(), impact.affectedSheetCount(),
				impact.affectedSheets(), impact.maxDepth(), impact.riskScore(),
				impact.riskLevel());
	}
}
