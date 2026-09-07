package com.hyeok02.excelaiagent.analysis.application.result;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;

import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

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
		assertThat(result.impact()).isNull();
		assertThat(result.confidence()).isNull();
	}

	@Test
	void preservesMissingDetailsAsMissingInsteadOfReturningInvalidConfidence() {
		AiWorkbookInsights.Insight incomplete = new AiWorkbookInsights.Insight(
				"상세 정보 유실", null, null, null, "summary", "info",
				List.of("Sales!A1"), null, Double.NaN, null);
		AiWorkbookInsights.InsightReport report = new AiWorkbookInsights.InsightReport(
				"분석 결과", List.of(incomplete), List.of());

		AnalysisInsightResult.Insight result = InsightResultMapper.map(report).insights().getFirst();

		assertThat(result.fact()).isNull();
		assertThat(result.confidence()).isNull();
	}

	@Test
	void mapsInsightValidationSummaryAndPerInsightStatus() {
		AiWorkbookInsights.Insight verified = new AiWorkbookInsights.Insight(
				"검증 완료", "Sales!A1 값을 확인했습니다.", null, "업무 기준값입니다.",
				"summary", "info", List.of("Sales!A1"), null, 0.98,
				null, "verified", List.of());
		AiWorkbookInsights.InsightReport report = new AiWorkbookInsights.InsightReport(
				"검증 결과", List.of(verified), List.of(),
				new AiWorkbookInsights.Validation(2, 1, 0, 1, List.of("1건 차단")));

		AnalysisInsightResult.Report result = InsightResultMapper.map(report);

		assertThat(result.insights().getFirst().validationStatus()).isEqualTo("verified");
		assertThat(result.validation().blockedCount()).isEqualTo(1);
		assertThat(result.validation().notices()).containsExactly("1건 차단");
		assertThat(result.validation().overviewValidated()).isFalse();
	}

	@Test
	void carriesExplicitAiOverviewValidationToTheFrontendContract() {
		JsonMapper mapper = JsonMapper.builder().build();
		AiWorkbookInsights.InsightReport source = mapper.readValue("""
				{
				  "overview": "날짜별 식단과 영양량을 확인할 수 있는 급식표입니다.",
				  "insights": [], "limitations": [],
				  "validation": {
				    "generated_count": 0, "verified_count": 0,
				    "limited_count": 0, "blocked_count": 0, "notices": [],
				    "overview_validated": true
				  }
				}
				""", AiWorkbookInsights.InsightReport.class);

		AnalysisInsightResult.Report result = InsightResultMapper.map(source);

		assertThat(source.validation().overviewValidated()).isTrue();
		assertThat(result.validation().overviewValidated()).isTrue();
		assertThat(result.overview()).isEqualTo(source.overview());
		assertThat(mapper.readTree(mapper.writeValueAsString(result))
				.path("validation").path("overviewValidated").asBoolean()).isTrue();
	}

	@Test
	void legacyJsonAndFiveArgumentConstructorsDoNotClaimOverviewValidation() {
		JsonMapper mapper = JsonMapper.builder().build();
		AiWorkbookInsights.Validation legacy = mapper.readValue("""
				{"generated_count": 1, "verified_count": 1,
				 "limited_count": 0, "blocked_count": 0, "notices": []}
				""", AiWorkbookInsights.Validation.class);
		AnalysisInsightResult.Report result = InsightResultMapper.map(
				new AiWorkbookInsights.InsightReport("기존 요약", List.of(), List.of(), legacy));

		assertThat(legacy.overviewValidated()).isFalse();
		assertThat(result.validation().overviewValidated()).isFalse();
		assertThat(new AiWorkbookInsights.Validation(1, 1, 0, 0, List.of())
				.overviewValidated()).isFalse();
		assertThat(new AnalysisInsightResult.Validation(1, 1, 0, 0, List.of())
				.overviewValidated()).isFalse();
		assertThat(mapper.readValue("""
				{"generatedCount": 1, "verifiedCount": 1,
				 "limitedCount": 0, "blockedCount": 0, "notices": []}
				""", AnalysisInsightResult.Validation.class).overviewValidated()).isFalse();
		assertThat(mapper.readValue("""
				{"generated_count": 1, "verified_count": 1, "limited_count": 0,
				 "blocked_count": 0, "notices": [], "overview_validated": null}
				""", AiWorkbookInsights.Validation.class).overviewValidated()).isFalse();
	}
}
