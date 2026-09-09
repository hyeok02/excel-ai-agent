package com.hyeok02.excelaiagent.telegram.application;

import java.util.List;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisFormulaRiskResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import org.springframework.stereotype.Component;

@Component
public class TelegramMessageFormatter {
	private static final int MAX_BODY_LENGTH = 3600;
	private static final String REMOVED_CAUSE_REASON =
			"원인을 직접 입증하는 수식·메타데이터 근거가 없어 원인 문장을 제외했습니다.";

	private final AuthProperties authProperties;

	public TelegramMessageFormatter(AuthProperties authProperties) {
		this.authProperties = authProperties;
	}

	public String format(AnalysisResultDetails result) {
		StringBuilder message = new StringBuilder("📊 Excel 분석 완료\n");
		message.append("파일: ").append(clean(result.workbook().filename(), 180));

		AnalysisInsightResult.Report report = result.insightReport();
		if (report != null) {
			appendInsights(message, report);
		}
		else {
			message.append("\n\n분석 요약\n")
					.append("시트 ").append(result.workbook().sheetCount()).append("개를 분석했습니다.");
		}
		appendFormulaRisks(message, result.workbook().formulaRiskSummary());

		String link = authProperties.frontendBaseUrl()
				+ "/excel-analysis?id=" + result.analysisId();
		return clip(message.toString(), MAX_BODY_LENGTH)
				+ "\n\n🔗 상세 결과\n" + link;
	}

	private void appendInsights(StringBuilder message, AnalysisInsightResult.Report report) {
		List<AnalysisInsightResult.Insight> source = report.insights() == null
				? List.of() : report.insights();
		List<AnalysisInsightResult.Insight> visible = source.stream()
				.filter(this::canDisplay)
				.toList();
		boolean suppressed = visible.size() != source.size();
		String overview = canUseOverview(report, visible, suppressed)
				? report.overview()
				: visible.stream().limit(2).map(AnalysisInsightResult.Insight::fact)
						.reduce((left, right) -> left + " " + right)
						.orElse("원본 근거로 확인할 수 있는 인사이트가 없습니다.");
		message.append("\n\n핵심 결론\n").append(clean(overview, 900));
		if (!visible.isEmpty()) {
			message.append("\n\n주요 인사이트");
			visible.stream().limit(3).forEach(insight -> message
					.append("\n• ").append(clean(insight.title(), 140))
					.append(": ").append(clean(insight.fact(), 480)));
		}
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

	private void appendFormulaRisks(
			StringBuilder message, AnalysisFormulaRiskResult.Summary risks) {
		if (risks == null || risks.totalCount() == 0) {
			return;
		}
		message.append("\n\n⚠️ 이상 징후: 총 ").append(risks.totalCount()).append("건")
				.append(" (오류 ").append(risks.errorCount())
				.append("건, 경고 ").append(risks.warningCount()).append("건)");
	}

	private String clean(String value, int limit) {
		String normalized = hasText(value) ? value.replaceAll("\\s+", " ").trim() : "-";
		return clip(normalized, limit);
	}

	private String clip(String value, int limit) {
		return value.length() <= limit ? value : value.substring(0, limit - 1) + "…";
	}

	private boolean hasText(String value) {
		return value != null && !value.isBlank();
	}
}
