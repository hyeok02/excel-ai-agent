package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;
import java.util.Objects;

public record AiSemanticClassification(
		SemanticRole role,
		double confidence,
		List<AiSemanticReason> reasons) {

	public AiSemanticClassification {
		Objects.requireNonNull(role, "의미 역할은 필수입니다.");
		if (confidence < 0 || confidence > 1) {
			throw new IllegalArgumentException("의미 역할 신뢰도는 0 이상 1 이하여야 합니다.");
		}
		reasons = reasons == null ? List.of() : List.copyOf(reasons);
	}
}
