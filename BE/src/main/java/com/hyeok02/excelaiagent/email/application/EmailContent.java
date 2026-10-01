package com.hyeok02.excelaiagent.email.application;

import java.util.List;

/** 메일 본문을 그리는 데 필요한 값만 추려 담는다. */
record EmailContent(
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
