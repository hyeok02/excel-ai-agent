package com.hyeok02.excelaiagent.email.application;

/** 메일 본문 중 텍스트 버전. HTML을 읽지 못하는 메일 클라이언트가 이 쪽을 쓴다. */
final class EmailTextRenderer {
	private EmailTextRenderer() {
	}

	static String render(EmailContent content) {
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
}
