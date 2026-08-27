package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;
import java.util.Objects;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.model.AiProvenance;

public record AiSheetClassification(
		SheetRole role,
		SheetImportance importance,
		double confidence,
		@JsonProperty("importance_score") int importanceScore,
		List<AiSheetRoleReason> reasons,
		AiProvenance provenance) {

	public AiSheetClassification(
			SheetRole role, SheetImportance importance, double confidence,
			int importanceScore, List<AiSheetRoleReason> reasons) {
		this(role, importance, confidence, importanceScore, reasons, null);
	}

	public AiSheetClassification {
		Objects.requireNonNull(role, "시트 역할은 필수입니다.");
		Objects.requireNonNull(importance, "시트 중요도는 필수입니다.");
		if (confidence < 0 || confidence > 1) {
			throw new IllegalArgumentException("시트 역할 신뢰도는 0 이상 1 이하여야 합니다.");
		}
		if (importanceScore < 0 || importanceScore > 100) {
			throw new IllegalArgumentException("시트 중요도 점수는 0 이상 100 이하여야 합니다.");
		}
		reasons = reasons == null ? List.of() : List.copyOf(reasons);
	}
}
