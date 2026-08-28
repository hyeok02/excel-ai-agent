package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisFormulaRiskResult {
	private AnalysisFormulaRiskResult() {
	}

	public record Summary(
			int totalCount,
			int errorCount,
			int warningCount,
			int brokenReferenceCount,
			int missingSheetCount,
			int externalReferenceCount,
			int dynamicFunctionCount,
			List<Finding> findings) {
	}

	public record Finding(
			String kind,
			String severity,
			String sheetName,
			String cell,
			String message,
			String formula,
			String reference,
			String functionName,
			AnalysisProvenanceResult.Provenance provenance) {
	}
}
