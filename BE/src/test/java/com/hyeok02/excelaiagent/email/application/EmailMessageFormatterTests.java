package com.hyeok02.excelaiagent.email.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisWorkbookResult;
import org.junit.jupiter.api.Test;

class EmailMessageFormatterTests {
	private final EmailMessageFormatter formatter = new EmailMessageFormatter();

	@Test
	void formatsBrandedHtmlAndPlainTextWithEscapedDynamicContent() {
		AnalysisInsightResult.Insight insight = verifiedInsight(
				"성장 <script>alert(1)</script>",
				"매출은 12% 증가했고 A&B “핵심” 지표가 개선됐습니다.");
		AnalysisInsightResult.Report report = new AnalysisInsightResult.Report(
				"<script>alert(2)</script> 핵심 & 결론 \"확인\"",
				List.of(insight),
				List.of(),
				new AnalysisInsightResult.Validation(1, 1, 0, 0, List.of(), true));
		String detailsUrl = "https://example.com/shared/analysis/token?from=email&lang=ko";

		FormattedEmail email = formatter.format(
				result("분기 <script> & \"실적\".xlsx", 3, report),
				detailsUrl);

		assertThat(email.subject())
				.contains("Excel AI Agent", "분기 <script>")
				.doesNotContain("\r", "\n");
		assertThat(email.plainTextBody())
				.contains("Excel 분석이 완료되었습니다.", "핵심 결론", "주요 인사이트")
				.contains(detailsUrl)
				.contains("매출은 12% 증가");
		assertThat(email.htmlBody())
				.contains("<!doctype html>", "<html lang=\"ko\">", "charset=\"UTF-8\"")
				.contains("Excel AI Agent", "ANALYSIS COMPLETE", "BIST", "elligence")
				.contains("상세 분석 결과 보기")
				.contains("&lt;script&gt;alert(2)&lt;/script&gt;")
				.contains("A&amp;B", "&quot;실적&quot;")
				.contains("href=\"https://example.com/shared/analysis/token?from=email&amp;lang=ko\"")
				.doesNotContain("<script>alert(1)</script>", "<script>alert(2)</script>")
				.endsWith("</html>\n");
	}

	@Test
	void rendersOnlyDisplayableInsightsAndCapsListAtFive() {
		List<AnalysisInsightResult.Insight> insights = new ArrayList<>();
		for (int index = 1; index <= 6; index++) {
			insights.add(verifiedInsight("인사이트 " + index, "검증된 사실 " + index));
		}
		insights.add(new AnalysisInsightResult.Insight(
				"차단 인사이트", "risk", "표시되면 안 됩니다", null, null,
				"위험", "critical", List.of("Sheet1!A1"), null, 0.2,
				"blocked", List.of("검증 실패")));
		AnalysisInsightResult.Report report = new AnalysisInsightResult.Report(
				"검증된 개요", insights, List.of(),
				new AnalysisInsightResult.Validation(7, 6, 0, 1, List.of(), false));

		FormattedEmail email = formatter.format(
				result("insights.xlsx", 2, report),
				"https://example.com/shared/analysis/token");

		assertThat(email.plainTextBody())
				.contains("인사이트 1", "인사이트 5")
				.doesNotContain("인사이트 6", "차단 인사이트");
		assertThat(email.htmlBody())
				.contains("인사이트 1", "인사이트 5")
				.doesNotContain("인사이트 6", "차단 인사이트");
		assertThat(count(email.htmlBody(), "<h3 style=\"")).isEqualTo(5);
	}

	@Test
	void formatsFallbackSummaryWhenInsightReportIsMissing() {
		FormattedEmail email = formatter.format(
				result("fallback.xlsx", 4, null),
				"https://example.com/shared/analysis/fallback");

		assertThat(email.plainTextBody())
				.contains("시트 4개를 분석했습니다.")
				.contains("https://example.com/shared/analysis/fallback");
		assertThat(email.htmlBody())
				.contains("시트 4개를 분석했습니다.")
				.contains("공유 가능한 검증 인사이트가 없습니다.")
				.contains("상세 분석 결과 보기")
				.endsWith("</html>\n");
	}

	private AnalysisResultDetails result(
			String filename,
			int sheetCount,
			AnalysisInsightResult.Report report) {
		AnalysisWorkbookResult.Workbook workbook = new AnalysisWorkbookResult.Workbook(
				filename, sheetCount, sheetCount, 0, List.of(), List.of(), null, null);
		return new AnalysisResultDetails(
				UUID.fromString("00000000-0000-0000-0000-000000000123"),
				Instant.parse("2026-09-30T04:43:00Z"),
				workbook,
				report,
				true);
	}

	private AnalysisInsightResult.Insight verifiedInsight(String title, String fact) {
		return new AnalysisInsightResult.Insight(
				title, "trend", fact, null, null, "핵심 지표", "info",
				List.of("Sheet1!A1:B4"), null, 0.98, "verified", List.of());
	}

	private int count(String value, String needle) {
		return (value.length() - value.replace(needle, "").length()) / needle.length();
	}
}
