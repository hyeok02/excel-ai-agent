package com.hyeok02.excelaiagent.integration.ai.model;

import java.util.List;

public record AiProvenance(
		String analyzer,
		String method,
		Double confidence,
		List<AiAnalysisEvidence> evidence) {
	public AiProvenance {
		evidence = evidence == null ? List.of() : List.copyOf(evidence);
	}
}
