package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.WorkbookQuestionHistoryService;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.WorkbookQuestionRepository;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import org.springframework.beans.factory.annotation.Autowired;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

abstract class WorkbookQuestionHistoryTestSupport extends AnalysisControllerTestSupport {
	@Autowired WorkbookQuestionRepository questionRepository;
	@Autowired WorkbookQuestionHistoryService historyService;
	@Autowired ObjectMapper objectMapper;

	protected UUID completed(String owner) {
		Instant now = Instant.now();
		UUID id = UUID.randomUUID();
		AnalysisJob job = AnalysisJob.queued(id, AnalysisMode.BFS, "history.xlsx", "xlsx", 100, owner, false, now);
		job.markProcessing(now);
		job.markCompleted(now);
		analysisJobRepository.saveAndFlush(job);
		analysisFileStorage.store(id, "xlsx", excel("history.xlsx"));
		return id;
	}

	protected JsonNode history(UUID id, String before, String size) throws Exception {
		var request = get("/api/v1/analyses/{id}/questions", id);
		if (before != null) request.param("before", before);
		if (size != null) request.param("size", size);
		return objectMapper.readTree(mockMvc.perform(request).andExpect(status().isOk())
				.andReturn().getResponse().getContentAsString());
	}

	protected void assertQuestions(JsonNode page, String... expected) {
		List<String> questions = page.get("items").valueStream()
				.map(item -> item.get("answer").get("question").asString()).toList();
		assertThat(questions).containsExactly(expected);
	}

	protected AiWorkbookQuestion answer(String question, String status) {
		return new AiWorkbookQuestion(question, "일부 확인된 답변", status, 0.75,
				List.of("query_workbook", "calculate"), List.of(
						new AiWorkbookQuestion.Evidence("cell", "실적", "C12", "원본", 71183.31159,
								"=SUM(C1:C11)", "매출", "#,##0.00"),
						new AiWorkbookQuestion.Evidence("range", "실적", "A1:B2", "항목",
								Map.of("values", List.of("회사", 42, false)), null, "대상", null)),
				List.of("모델의 대상 해석을 포함합니다.", "일부 범위는 확인하지 못했습니다."),
				new AiWorkbookQuestion.Verification("source_checked", List.of("semantic_alias_resolved", "context_resolved")),
				"이전 회사의 2026년 예상 매출은?");
	}
}
