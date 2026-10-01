package com.hyeok02.excelaiagent.email.application;

/** 메일에 싣는 인사이트 한 건. */
record InsightContent(
		String title,
		String fact,
		String category,
		String validationLabel,
		boolean verified) {
}
