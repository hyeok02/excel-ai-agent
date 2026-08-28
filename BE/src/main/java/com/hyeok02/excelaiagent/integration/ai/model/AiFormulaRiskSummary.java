package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiFormulaRiskSummary(
		@JsonProperty("total_count") int totalCount,
		@JsonProperty("error_count") int errorCount,
		@JsonProperty("warning_count") int warningCount,
		@JsonProperty("broken_reference_count") int brokenReferenceCount,
		@JsonProperty("missing_sheet_count") int missingSheetCount,
		@JsonProperty("external_reference_count") int externalReferenceCount,
		@JsonProperty("dynamic_function_count") int dynamicFunctionCount,
		@JsonProperty("pattern_mismatch_count") int patternMismatchCount,
		@JsonProperty("hardcoded_value_count") int hardcodedValueCount,
		@JsonProperty("high_risk_count") int highRiskCount,
		@JsonProperty("critical_risk_count") int criticalRiskCount,
		List<AiFormulaRiskFinding> findings) {

	public AiFormulaRiskSummary {
		findings = findings == null ? List.of() : List.copyOf(findings);
	}

	public static AiFormulaRiskSummary empty() {
		return new AiFormulaRiskSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, List.of());
	}
}
