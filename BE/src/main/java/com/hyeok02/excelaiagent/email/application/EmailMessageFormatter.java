package com.hyeok02.excelaiagent.email.application;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisWorkbookResult;
import org.springframework.stereotype.Component;

@Component
public class EmailMessageFormatter {
	private static final int MAX_FILENAME_LENGTH = 180;
	private static final int MAX_OVERVIEW_LENGTH = 1800;
	private static final int MAX_INSIGHT_TITLE_LENGTH = 180;
	private static final int MAX_INSIGHT_FACT_LENGTH = 900;
	private static final int MAX_DETAILS_URL_LENGTH = 2000;
	private static final int MAX_VISIBLE_INSIGHTS = 5;
	private static final String REMOVED_CAUSE_REASON =
			"원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.";
	private static final DateTimeFormatter COMPLETED_AT_FORMATTER =
			DateTimeFormatter.ofPattern("yyyy.MM.dd HH:mm", Locale.KOREAN)
					.withZone(ZoneId.of("Asia/Seoul"));

	public FormattedEmail format(AnalysisResultDetails result, String detailsUrl) {
		AnalysisWorkbookResult.Workbook workbook = result.workbook();
		String filename = clean(workbook.filename(), MAX_FILENAME_LENGTH);
		List<AnalysisInsightResult.Insight> visibleInsights = visibleInsights(
				result.insightReport());
		String overview = overview(result, visibleInsights);
		List<InsightContent> insights = visibleInsights.stream()
				.limit(MAX_VISIBLE_INSIGHTS)
				.map(this::toInsightContent)
				.toList();
		List<AnalysisWorkbookResult.Sheet> sheets = workbook.sheets() == null
				? List.of() : workbook.sheets();

		EmailContent content = new EmailContent(
				filename,
				result.analysisId() == null ? "-" : result.analysisId().toString(),
				result.createdAt() == null ? "-"
						: COMPLETED_AT_FORMATTER.format(result.createdAt()),
				Math.max(0, workbook.sheetCount()),
				sheets.stream().mapToInt(sheet -> Math.max(0, sheet.regionCount())).sum(),
				sheets.stream().mapToInt(sheet -> Math.max(0, sheet.formulaCount())).sum(),
				sheets.stream().mapToInt(sheet -> Math.max(0, sheet.tableCount())).sum(),
				sheets.stream().mapToInt(sheet -> Math.max(0, sheet.chartCount())).sum(),
				overview,
				insights,
				clean(detailsUrl, MAX_DETAILS_URL_LENGTH));

		return new FormattedEmail(
				"[Excel AI Agent] " + cleanHeader(filename) + " 분석 결과",
				EmailTextRenderer.render(content),
				EmailHtmlRenderer.render(content));
	}

	private List<AnalysisInsightResult.Insight> visibleInsights(
			AnalysisInsightResult.Report report) {
		if (report == null || report.insights() == null) {
			return List.of();
		}
		return report.insights().stream()
				.filter(this::canDisplay)
				.toList();
	}

	private String overview(
			AnalysisResultDetails result,
			List<AnalysisInsightResult.Insight> visibleInsights) {
		AnalysisInsightResult.Report report = result.insightReport();
		if (report == null) {
			return "시트 " + Math.max(0, result.workbook().sheetCount())
					+ "개를 분석했습니다. 상세 결과에서 분석 내용을 확인해 주세요.";
		}
		List<AnalysisInsightResult.Insight> source = report.insights() == null
				? List.of() : report.insights();
		boolean suppressed = visibleInsights.size() != source.size();
		if (canUseOverview(report, visibleInsights, suppressed)) {
			return clean(report.overview(), MAX_OVERVIEW_LENGTH);
		}
		return visibleInsights.stream()
				.limit(2)
				.map(AnalysisInsightResult.Insight::fact)
				.map(fact -> clean(fact, MAX_INSIGHT_FACT_LENGTH))
				.reduce((left, right) -> left + " " + right)
				.orElse("원본 근거로 확인할 수 있는 인사이트가 없습니다.");
	}

	private InsightContent toInsightContent(AnalysisInsightResult.Insight insight) {
		String category = hasText(insight.category())
				? insight.category() : insight.topic();
		return new InsightContent(
				clean(insight.title(), MAX_INSIGHT_TITLE_LENGTH),
				clean(insight.fact(), MAX_INSIGHT_FACT_LENGTH),
				clean(category, 48),
				"verified".equals(insight.validationStatus())
						? "검증 완료" : "제한적 검증",
				"verified".equals(insight.validationStatus()));
	}

	private boolean canDisplay(AnalysisInsightResult.Insight insight) {
		if (!hasText(insight.fact()) || insight.evidence() == null
				|| insight.evidence().stream().noneMatch(this::hasText)) {
			return false;
		}
		List<String> reasons = insight.validationReasons() == null
				? List.of() : insight.validationReasons();
		if (reasons.stream().anyMatch(reason -> !REMOVED_CAUSE_REASON.equals(reason))) {
			return false;
		}
		return "verified".equals(insight.validationStatus())
				|| ("limited".equals(insight.validationStatus()) && !reasons.isEmpty());
	}

	private boolean canUseOverview(
			AnalysisInsightResult.Report report,
			List<AnalysisInsightResult.Insight> visible,
			boolean suppressed) {
		return report.validation() != null
				&& report.validation().overviewValidated()
				&& !suppressed && !visible.isEmpty() && hasText(report.overview());
	}

	private String clean(String value, int limit) {
		String normalized = hasText(value) ? value.replaceAll("\\s+", " ").trim() : "-";
		return clip(normalized, limit);
	}

	private String cleanHeader(String value) {
		return value.replaceAll("[\\r\\n]+", " ").trim();
	}

	private String clip(String value, int limit) {
		return value.length() <= limit ? value : value.substring(0, limit - 1) + "…";
	}

	private boolean hasText(String value) {
		return value != null && !value.isBlank();
	}
}
