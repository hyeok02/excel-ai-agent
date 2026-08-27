package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

public final class AnalysisProvenanceResult {
	private AnalysisProvenanceResult() {
	}

	public record Provenance(
			String analyzer,
			String method,
			Double confidence,
			List<Evidence> evidence) {
	}

	public record Evidence(
			String kind,
			String sheetName,
			String reference,
			String description,
			Object value,
			String formula) {
	}
}
