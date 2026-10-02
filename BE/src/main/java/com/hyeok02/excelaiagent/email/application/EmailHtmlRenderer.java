package com.hyeok02.excelaiagent.email.application;

import org.springframework.web.util.HtmlUtils;

/** 메일 본문 HTML의 바깥 틀. 숫자 요약과 인사이트 카드는 EmailInsightCards가 그린다. */
final class EmailHtmlRenderer {
	private EmailHtmlRenderer() {
	}

	static String render(EmailContent content) {
		String filename = EmailHtmlRenderer.escape(content.filename());
		String analysisId = EmailHtmlRenderer.escape(content.analysisId());
		String completedAt = EmailHtmlRenderer.escape(content.completedAt());
		String overview = EmailHtmlRenderer.escape(content.overview());
		String detailsUrl = EmailHtmlRenderer.escape(content.detailsUrl());
		String preheader = EmailHtmlRenderer.escape(content.filename()
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
				EmailInsightCards.metrics(content),
				overview));

		html.append(EmailInsightCards.insights(content.insights()));
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

	static String escape(String value) {
		return HtmlUtils.htmlEscape(value == null ? "" : value, "UTF-8");
	}
}
