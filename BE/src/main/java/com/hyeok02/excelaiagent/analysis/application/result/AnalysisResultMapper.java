package com.hyeok02.excelaiagent.analysis.application.result;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;

public final class AnalysisResultMapper {
	private AnalysisResultMapper() {
	}

	public static AnalysisResultDetails map(
			UUID analysisId, Instant createdAt, AiWorkbookInsights analysis) {
		return new AnalysisResultDetails(
				analysisId,
				createdAt,
				WorkbookResultMapper.map(analysis.workbook()),
				InsightResultMapper.map(analysis.report()),
				true);
	}
}
