package com.hyeok02.excelaiagent.email.application;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;

import com.hyeok02.excelaiagent.analysis.application.AnalysisResultDetails;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisInsightResult;
import com.hyeok02.excelaiagent.analysis.application.result.AnalysisWorkbookResult;
import org.springframework.stereotype.Component;
import org.springframework.web.util.HtmlUtils;

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
				renderPlainText(content),
				renderHtml(content));
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

	private String renderPlainText(EmailContent content) {
		StringBuilder body = new StringBuilder();
		body.append("Excel 분석이 완료되었습니다.\n\n")
				.append("파일: ").append(content.filename()).append('\n')
				.append("완료 시각: ").append(content.completedAt()).append('\n')
				.append("분석 범위: 시트 ").append(content.sheetCount())
				.append("개 · 데이터 영역 ").append(content.regionCount())
				.append("개 · 수식 ").append(content.formulaCount()).append("개\n\n")
				.append("핵심 결론\n")
				.append(content.overview());

		if (!content.insights().isEmpty()) {
			body.append("\n\n주요 인사이트");
			for (int index = 0; index < content.insights().size(); index++) {
				InsightContent insight = content.insights().get(index);
				body.append("\n")
						.append(index + 1).append(". ")
						.append(insight.title()).append("\n   ")
						.append(insight.fact());
			}
		}

		return body.append("\n\n상세 분석 결과 보기\n")
				.append(content.detailsUrl())
				.append("\n\n이 메일은 Excel AI Agent에서 자동 발송되었습니다. ")
				.append("원본 Excel 파일은 첨부되지 않습니다.")
				.toString();
	}

	private String renderHtml(EmailContent content) {
		String filename = html(content.filename());
		String analysisId = html(content.analysisId());
		String completedAt = html(content.completedAt());
		String overview = html(content.overview());
		String detailsUrl = html(content.detailsUrl());
		String preheader = html(content.filename()
				+ " 분석 결과가 준비되었습니다. 핵심 결론과 주요 인사이트를 확인하세요.");

		StringBuilder html = new StringBuilder();
		html.append("""
				<!doctype html>
				<html lang="ko">
				<head>
				  <meta charset="UTF-8">
				  <meta name="viewport" content="width=device-width, initial-scale=1.0">
				  <meta name="color-scheme" content="light">
				  <title>Excel AI Agent 분석 결과</title>
				  <style>
				    @media only screen and (max-width: 680px) {
				      .email-shell { width: 100%% !important; }
				      .mobile-pad { padding-left: 18px !important; padding-right: 18px !important; }
				      .metric-value { font-size: 18px !important; }
				      .hero-title { font-size: 25px !important; line-height: 1.25 !important; }
				    }
				  </style>
				</head>
				<body style="margin:0;padding:0;background-color:#f5f7fa;color:#0f172a;font-family:'Apple SD Gothic Neo','Malgun Gothic','Segoe UI',Arial,sans-serif;">
				  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;line-height:1px;font-size:1px;">%s</div>
				  <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0" style="width:100%%;background-color:#f5f7fa;">
				    <tr>
				      <td align="center" style="padding:32px 14px;">
				        <table role="presentation" width="640" cellspacing="0" cellpadding="0" border="0" class="email-shell" style="width:100%%;max-width:640px;background-color:#ffffff;border:1px solid #e2e8f0;border-radius:24px;box-shadow:0 12px 36px rgba(15,23,42,.06);overflow:hidden;">
				          <tr>
				            <td class="mobile-pad" style="padding:22px 28px;border-bottom:1px solid #e2e8f0;background-color:#ffffff;">
				              <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0">
				                <tr>
				                  <td valign="middle">
				                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
				                      <tr>
				                        <td align="center" valign="middle" width="38" height="38" style="width:38px;height:38px;border-radius:12px;background-color:#2563eb;color:#ffffff;font-size:20px;font-weight:800;box-shadow:0 8px 18px rgba(37,99,235,.24);">✦</td>
				                        <td style="padding-left:11px;">
				                          <div style="font-size:15px;line-height:20px;font-weight:800;color:#0f172a;">Excel AI Agent</div>
				                          <div style="font-size:10px;line-height:15px;font-weight:700;letter-spacing:.14em;color:#94a3b8;">DECISION SUPPORT</div>
				                        </td>
				                      </tr>
				                    </table>
				                  </td>
				                  <td align="right" valign="middle" style="font-size:15px;font-weight:800;white-space:nowrap;"><span style="color:#1e40af;">BIST</span><span style="color:#0ea5e9;">elligence</span></td>
				                </tr>
				              </table>
				            </td>
				          </tr>
				          <tr>
				            <td class="mobile-pad" style="padding:26px 28px 0;">
				              <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0" style="background-color:#2563eb;background-image:linear-gradient(135deg,#1d4ed8 0%%,#2563eb 55%%,#0ea5e9 100%%);border-radius:20px;overflow:hidden;">
				                <tr>
				                  <td style="padding:32px 30px 34px;color:#ffffff;">
				                    <span style="display:inline-block;padding:6px 10px;border:1px solid rgba(255,255,255,.24);border-radius:999px;background-color:rgba(255,255,255,.12);font-size:10px;line-height:14px;font-weight:800;letter-spacing:.14em;color:#dbeafe;">ANALYSIS COMPLETE</span>
				                    <h1 class="hero-title" style="margin:18px 0 8px;font-size:30px;line-height:1.25;letter-spacing:-.04em;color:#ffffff;">분석 결과가 준비되었습니다</h1>
				                    <p style="margin:0;font-size:15px;line-height:1.6;font-weight:700;color:#eff6ff;word-break:break-all;">%s</p>
				                    <p style="margin:17px 0 0;font-size:11px;line-height:1.6;color:#bfdbfe;">%s 완료&nbsp;&nbsp;·&nbsp;&nbsp;분석 ID %s</p>
				                  </td>
				                </tr>
				              </table>
				            </td>
				          </tr>
				          <tr>
				            <td class="mobile-pad" style="padding:18px 28px 0;">
				              <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #e2e8f0;border-radius:16px;background-color:#ffffff;overflow:hidden;">
				                <tr>
				                  %s
				                </tr>
				              </table>
				            </td>
				          </tr>
				          <tr>
				            <td class="mobile-pad" style="padding:30px 28px 0;">
				              <p style="margin:0 0 10px;font-size:10px;line-height:14px;font-weight:800;letter-spacing:.14em;color:#2563eb;">EXECUTIVE SUMMARY</p>
				              <h2 style="margin:0 0 14px;font-size:20px;line-height:1.35;letter-spacing:-.025em;color:#0f172a;">핵심 결론</h2>
				              <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #dbeafe;border-radius:16px;background-color:#eff6ff;">
				                <tr>
				                  <td style="padding:22px 22px 23px;font-size:15px;line-height:1.75;color:#1e293b;word-break:keep-all;">%s</td>
				                </tr>
				              </table>
				            </td>
				          </tr>
					""".formatted(
				preheader,
				filename,
				completedAt,
				analysisId,
				renderMetricCells(content),
				overview));

		html.append(renderInsights(content.insights()));
		html.append("""
				          <tr>
				            <td class="mobile-pad" style="padding:30px 28px 32px;">
				              <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0">
				                <tr>
				                  <td align="center" style="border-radius:13px;background-color:#2563eb;box-shadow:0 10px 24px rgba(37,99,235,.24);">
				                    <a href="%s" style="display:block;padding:15px 22px;font-size:14px;line-height:20px;font-weight:800;text-decoration:none;color:#ffffff;border-radius:13px;">상세 분석 결과 보기&nbsp;&nbsp;→</a>
				                  </td>
				                </tr>
				              </table>
				              <p style="margin:13px 0 0;text-align:center;font-size:11px;line-height:1.6;color:#64748b;">수신자 전용 보안 링크입니다. 버튼이 열리지 않으면 아래 주소를 브라우저에 붙여 넣어 주세요.</p>
				              <p style="margin:5px 0 0;text-align:center;font-size:10px;line-height:1.5;color:#94a3b8;word-break:break-all;"><a href="%s" style="color:#64748b;text-decoration:underline;">%s</a></p>
				            </td>
				          </tr>
				          <tr>
				            <td class="mobile-pad" style="padding:19px 28px 22px;border-top:1px solid #e2e8f0;background-color:#f8fafc;">
				              <p style="margin:0;font-size:11px;line-height:1.65;color:#64748b;">이 메일은 <strong style="color:#334155;">Excel AI Agent</strong>에서 자동 발송되었습니다.<br>원본 Excel 파일은 첨부되지 않으며, 상세 분석은 위의 보안 링크에서 확인할 수 있습니다.</p>
				            </td>
				          </tr>
				        </table>
				      </td>
				    </tr>
				  </table>
				</body>
				</html>
				""".formatted(detailsUrl, detailsUrl, detailsUrl));
		return html.toString();
	}

	private String renderMetricCells(EmailContent content) {
		return metricCell("분석 시트", content.sheetCount(), false)
				+ metricCell("데이터 영역", content.regionCount(), false)
				+ metricCell("수식", content.formulaCount(), false)
				+ metricCell("테이블", content.tableCount(), false)
				+ metricCell("차트", content.chartCount(), true);
	}

	private String metricCell(String label, int value, boolean last) {
		String border = last ? "" : "border-right:1px solid #e2e8f0;";
		return """
				<td align="center" width="20%%" style="width:20%%;padding:16px 5px;%s">
				  <div class="metric-value" style="font-size:21px;line-height:25px;font-weight:800;color:#0f172a;">%d</div>
				  <div style="margin-top:3px;font-size:9px;line-height:13px;font-weight:700;color:#94a3b8;white-space:nowrap;">%s</div>
				</td>
				""".formatted(border, value, label);
	}

	private String renderInsights(List<InsightContent> insights) {
		StringBuilder section = new StringBuilder("""
				          <tr>
				            <td class="mobile-pad" style="padding:30px 28px 0;">
				              <p style="margin:0 0 10px;font-size:10px;line-height:14px;font-weight:800;letter-spacing:.14em;color:#2563eb;">KEY INSIGHTS</p>
				              <h2 style="margin:0 0 14px;font-size:20px;line-height:1.35;letter-spacing:-.025em;color:#0f172a;">주요 인사이트</h2>
				""");
		if (insights.isEmpty()) {
			section.append("""
								<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px dashed #bfdbfe;border-radius:16px;background-color:#f8fafc;">
								  <tr><td align="center" style="padding:23px;font-size:13px;line-height:1.6;color:#64748b;">공유 가능한 검증 인사이트가 없습니다.<br>상세 결과에서 전체 분석 내용을 확인해 주세요.</td></tr>
								</table>
								""");
		}
		else {
			for (int index = 0; index < insights.size(); index++) {
				section.append(renderInsightCard(index + 1, insights.get(index)));
			}
		}
		return section.append("""
				            </td>
				          </tr>
				""").toString();
	}

	private String renderInsightCard(int number, InsightContent insight) {
		String statusBackground = insight.verified() ? "#ecfdf5" : "#fffbeb";
		String statusColor = insight.verified() ? "#047857" : "#b45309";
		return """
				<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 12px;border:1px solid #e2e8f0;border-radius:16px;background-color:#ffffff;">
				  <tr>
				    <td style="padding:19px 20px 20px;">
				      <table role="presentation" width="100%%" cellspacing="0" cellpadding="0" border="0">
				        <tr>
				          <td valign="middle"><span style="display:inline-block;padding:4px 8px;border-radius:999px;background-color:#f1f5f9;font-size:9px;line-height:13px;font-weight:800;letter-spacing:.08em;color:#64748b;">%02d&nbsp;&nbsp;%s</span></td>
				          <td align="right" valign="middle"><span style="display:inline-block;padding:4px 8px;border-radius:999px;background-color:%s;font-size:9px;line-height:13px;font-weight:800;color:%s;">●&nbsp; %s</span></td>
				        </tr>
				      </table>
				      <h3 style="margin:13px 0 7px;font-size:16px;line-height:1.45;letter-spacing:-.015em;color:#0f172a;">%s</h3>
				      <p style="margin:0;font-size:13px;line-height:1.72;color:#334155;word-break:keep-all;">%s</p>
				    </td>
				  </tr>
				</table>
				""".formatted(
				number,
				html(insight.category()),
				statusBackground,
				statusColor,
				html(insight.validationLabel()),
				html(insight.title()),
				html(insight.fact()));
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

	private String html(String value) {
		return HtmlUtils.htmlEscape(value == null ? "" : value, "UTF-8");
	}

	private boolean hasText(String value) {
		return value != null && !value.isBlank();
	}

	private record EmailContent(
			String filename,
			String analysisId,
			String completedAt,
			int sheetCount,
			int regionCount,
			int formulaCount,
			int tableCount,
			int chartCount,
			String overview,
			List<InsightContent> insights,
			String detailsUrl) {
	}

	private record InsightContent(
			String title,
			String fact,
			String category,
			String validationLabel,
			boolean verified) {
	}
}
