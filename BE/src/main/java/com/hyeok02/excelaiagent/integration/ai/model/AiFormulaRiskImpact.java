package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record AiFormulaRiskImpact(
		@JsonProperty("affected_formula_count") int affectedFormulaCount,
		@JsonProperty("affected_sheet_count") int affectedSheetCount,
		@JsonProperty("affected_sheets") List<String> affectedSheets,
		@JsonProperty("max_depth") int maxDepth,
		@JsonProperty("risk_score") int riskScore,
		@JsonProperty("risk_level") String riskLevel) {

	public AiFormulaRiskImpact {
		affectedSheets = affectedSheets == null ? List.of() : List.copyOf(affectedSheets);
	}
}
