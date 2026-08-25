package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisResultMapper;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisWorkbookResult;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;

public record AnalysisResultDetails(
		UUID analysisId,
		Instant createdAt,
		AnalysisWorkbookResult.Workbook workbook,
		AnalysisInsightResult.Report insightReport) {

	public static AnalysisResultDetails from(
			UUID analysisId, Instant createdAt, AiWorkbookInsights workbookAnalysis) {
		return AnalysisResultMapper.map(analysisId, createdAt, workbookAnalysis);
	}
}
