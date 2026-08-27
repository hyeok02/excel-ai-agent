package com.hyeok02.excelaiagent.integration.ai;

import java.util.Objects;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hyeok02.excelaiagent.integration.ai.model.AiProvenance;

public record AiAnalysisInclusion(
		AnalysisDecision decision,
		@JsonProperty("reason_code") String reasonCode,
		String reason,
		AiProvenance provenance) {

	public AiAnalysisInclusion(AnalysisDecision decision, String reasonCode, String reason) {
		this(decision, reasonCode, reason, null);
	}

	public AiAnalysisInclusion {
		Objects.requireNonNull(decision, "분석 포함 결정은 필수입니다.");
		if (reasonCode == null || reasonCode.isBlank()) {
			throw new IllegalArgumentException("분석 포함 판단 사유 코드는 필수입니다.");
		}
		if (reason == null || reason.isBlank()) {
			throw new IllegalArgumentException("분석 포함 판단 설명은 필수입니다.");
		}
	}
}
