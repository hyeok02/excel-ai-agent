package com.hyeok02.excelaiagent.analysis.application;

import java.util.List;

public record AnalysisHistoryPage(
		List<AnalysisDetails> content,
		int page,
		int size,
		long totalElements,
		int totalPages,
		boolean hasNext) {

	public AnalysisHistoryPage {
		content = List.copyOf(content);
	}
}
