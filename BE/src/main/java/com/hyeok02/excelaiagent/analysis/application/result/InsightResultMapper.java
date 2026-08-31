package com.hyeok02.excelaiagent.analysis.application.result;

import java.util.List;

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
				report.limitations(),
				mapValidation(report.validation()));
	}

	private static AnalysisInsightResult.Insight mapInsight(AiWorkbookInsights.Insight insight) {
		String fact = hasText(insight.fact()) ? insight.fact() : insight.description();
		String impact = hasText(insight.impact())
				? insight.impact()
				: "과거 분석 결과에는 영향 정보가 제공되지 않았습니다.";
		Double confidence = normalizeConfidence(insight.confidence());
		return new AnalysisInsightResult.Insight(
				insight.title(), fact, insight.cause(), impact,
				insight.category(), insight.severity(), insight.evidence(),
				insight.recommendation(), confidence, insight.validationStatus(),
				insight.validationReasons() == null ? List.of() : insight.validationReasons());
	}

	private static AnalysisInsightResult.Validation mapValidation(AiWorkbookInsights.Validation validation) {
		if (validation == null) {
			return null;
		}
		return new AnalysisInsightResult.Validation(
				validation.generatedCount(), validation.verifiedCount(),
				validation.limitedCount(), validation.blockedCount(),
				validation.notices() == null ? List.of() : validation.notices());
	}

	private static boolean hasText(String value) {
		return value != null && !value.isBlank();
	}

	private static Double normalizeConfidence(Double confidence) {
		if (confidence == null || !Double.isFinite(confidence)
				|| confidence < 0 || confidence > 1) {
			return null;
		}
		return confidence;
	}
}
