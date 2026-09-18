package com.hyeok02.excelaiagent.sharing.application;

import java.time.Instant;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisWorkbookResult;

public record AnalysisPublicShareView(
		Instant createdAt,
		Instant expiresAt,
		AnalysisWorkbookResult.Workbook workbook,
		AnalysisInsightResult.Report insightReport) {

	public static AnalysisPublicShareView from(
			AnalysisResultDetails result, Instant expiresAt) {
		return new AnalysisPublicShareView(
				result.createdAt(), expiresAt, result.workbook(), result.insightReport());
	}
}
