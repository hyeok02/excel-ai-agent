package com.hyeok02.excelaiagent.analysis.application.result;

import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;

final class InsightResultMapper {
	private InsightResultMapper() {
	}

	static AnalysisInsightResult.Report map(AiWorkbookInsights.InsightReport report) {
		if (report == null) {
			return null;
		}
		return new AnalysisInsightResult.Report(
				report.overview(),
				report.insights().stream().map(InsightResultMapper::mapInsight).toList(),
				report.limitations());
	}

	private static AnalysisInsightResult.Insight mapInsight(AiWorkbookInsights.Insight insight) {
		return new AnalysisInsightResult.Insight(
				insight.title(), insight.description(), insight.category(), insight.severity(),
				insight.evidence(), insight.recommendation());
	}
}
