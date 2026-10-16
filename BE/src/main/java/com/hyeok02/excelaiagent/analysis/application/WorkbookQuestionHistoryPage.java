package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.List;

import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;

public record WorkbookQuestionHistoryPage(List<Item> items, String nextCursor) {
	public record Item(String id, Instant createdAt, AiWorkbookQuestion answer) {
	}
}
