package com.hyeok02.excelaiagent.analysis.application.result;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import org.junit.jupiter.api.Test;

class InsightResultMapperTests {
	@Test
	void mapsLegacyDescriptionWithoutBreakingStoredAnalysisHistory() {
		AiWorkbookInsights.Insight legacy = new AiWorkbookInsights.Insight(
				"기존 인사이트", null, null, null, "summary", "info",
				List.of("Sales!A1"), null, null, "기존 description 형식의 사실입니다.");
		AiWorkbookInsights.InsightReport report = new AiWorkbookInsights.InsightReport(
				"기존 결과", List.of(legacy), List.of());

		AnalysisInsightResult.Insight result = InsightResultMapper.map(report).insights().getFirst();

		assertThat(result.fact()).isEqualTo("기존 description 형식의 사실입니다.");
		assertThat(result.impact()).contains("과거 분석 결과");
		assertThat(result.confidence()).isZero();
	}
}
