package com.hyeok02.excelaiagent.email.application;

import java.util.List;

/** 메일 HTML 가운데 숫자 요약과 인사이트 카드 부분. */
final class EmailInsightCards {
	private EmailInsightCards() {
	}

	static String metrics(EmailContent content) {
		return metricCell("분석 시트", content.sheetCount(), false)
				+ metricCell("데이터 영역", content.regionCount(), false)
				+ metricCell("수식", content.formulaCount(), false)
				+ metricCell("테이블", content.tableCount(), false)
				+ metricCell("차트", content.chartCount(), true);
	}

	private static String metricCell(String label, int value, boolean last) {
		String border = last ? "" : "border-right:1px solid #e2e8f0;";
		return """
				<td align="center" width="20%%" style="width:20%%;padding:16px 5px;%s">
				  <div class="metric-value" style="font-size:21px;line-height:25px;font-weight:800;color:#0f172a;">%d</div>
				  <div style="margin-top:3px;font-size:9px;line-height:13px;font-weight:700;color:#94a3b8;white-space:nowrap;">%s</div>
				</td>
				""".formatted(border, value, label);
	}

	static String insights(List<InsightContent> insights) {
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
				section.append(insightCard(index + 1, insights.get(index)));
			}
		}
		return section.append("""
				            </td>
				          </tr>
				""").toString();
	}

	private static String insightCard(int number, InsightContent insight) {
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
				EmailHtmlRenderer.escape(insight.category()),
				statusBackground,
				statusColor,
				EmailHtmlRenderer.escape(insight.validationLabel()),
				EmailHtmlRenderer.escape(insight.title()),
				EmailHtmlRenderer.escape(insight.fact()));
	}
}
