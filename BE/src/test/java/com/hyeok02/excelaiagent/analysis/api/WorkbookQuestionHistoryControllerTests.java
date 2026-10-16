package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.application.WorkbookQuestionHistoryService;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.WorkbookQuestionRepository;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class WorkbookQuestionHistoryControllerTests extends AnalysisControllerTestSupport {
	@Autowired WorkbookQuestionRepository questionRepository;
	@Autowired WorkbookQuestionHistoryService historyService;
	@Autowired ObjectMapper objectMapper;

	@ParameterizedTest
	@ValueSource(strings = {"answered", "limited", "insufficient_evidence"})
	void restoresEveryAnswerFieldWithoutReverification(String answerStatus) throws Exception {
		UUID id = completed("system");
		AiWorkbookQuestion answer = answer("2026년은?", answerStatus);
		when(aiServiceClient.askWorkbook(any(Resource.class), any(), anyBoolean())).thenReturn(answer);
		String posted = mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"  2026년은?  \"}"))
				.andExpect(status().isOk()).andReturn().getResponse().getContentAsString();

		JsonNode page = history(id, null, null);
		JsonNode item = page.get("items").get(0);
		assertThat(item.get("answer")).isEqualTo(objectMapper.readTree(posted));
		assertThat(item.get("id").isString()).isTrue();
		assertThat(Long.parseLong(item.get("id").asString())).isPositive();
		assertThat(Instant.parse(item.get("createdAt").asString())).isBeforeOrEqualTo(Instant.now());
		assertThat(page.get("nextCursor").isNull()).isTrue();
		assertThat(questionRepository.findAll().getFirst().getSubmittedQuestion()).isEqualTo("2026년은?");
		verify(aiServiceClient).askWorkbook(any(Resource.class), any(), anyBoolean());
	}

	@Test
	void storesUnknownVerificationAsUnverifiedAndKeepsNullableEvidence() throws Exception {
		UUID id = completed("system");
		AiWorkbookQuestion answer = new AiWorkbookQuestion(
				"어떤 뜻이야?", "설명을 확인할 수 없습니다.", "insufficient_evidence", 0,
				List.of(), List.of(new AiWorkbookQuestion.Evidence("cell", "자료", "A1", null,
						null, null, null, null)), List.of("원본 설명 없음"));
		historyService.save(id, "system", answer.question(), answer);

		JsonNode restored = history(id, null, null).get("items").get(0).get("answer");
		assertThat(restored).isEqualTo(objectMapper.valueToTree(answer));
		assertThat(restored.get("verification").get("level").asString()).isEqualTo("unverified");
	}

	@Test
	void returnsEmptyHistoryForOwnedAnalysisAndNotFoundForMissingAnalysis() throws Exception {
		UUID id = completed("system");
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", id))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items").isEmpty())
				.andExpect(jsonPath("$.nextCursor").isEmpty());
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", UUID.randomUUID()))
				.andExpect(status().isNotFound());
	}

	@Test
	void isolatesFilesAndOwnersForReadsAndWrites() throws Exception {
		UUID aliceFirst = completed("alice");
		UUID aliceSecond = completed("alice");
		UUID bob = completed("bob");
		historyService.save(aliceFirst, "alice", "first", answer("first", "limited"));
		historyService.save(aliceSecond, "alice", "second", answer("second", "answered"));
		historyService.save(bob, "bob", "private", answer("private", "answered"));

		mockMvc.perform(get("/api/v1/analyses/{id}/questions", aliceFirst).with(user("alice")))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items.length()").value(1))
				.andExpect(jsonPath("$.items[0].answer.question").value("first"));
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", bob).with(user("alice")))
				.andExpect(status().isNotFound());
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", bob).with(user("alice"))
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"private\"}"))
				.andExpect(status().isNotFound());
		assertThatThrownBy(() -> historyService.save(bob, "alice", "private", answer("private", "answered")))
				.isInstanceOf(AnalysisNotFoundException.class);
		assertThat(questionRepository.count()).isEqualTo(3);
		verify(aiServiceClient, never()).askWorkbook(any(Resource.class), any(), anyBoolean());
	}

	@Test
	void readsSavedAnswersAfterSourceExpiresButRejectsNewQuestion() throws Exception {
		UUID id = completed("system");
		historyService.save(id, "system", "original", answer("original", "limited"));
		analysisFileStorage.delete(id);

		mockMvc.perform(get("/api/v1/analyses/{id}/questions", id))
				.andExpect(status().isOk()).andExpect(jsonPath("$.items[0].answer.status").value("limited"));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"또 질문\"}"))
				.andExpect(status().isGone());
		assertThat(questionRepository.count()).isEqualTo(1);
		verify(aiServiceClient, never()).askWorkbook(any(Resource.class), any(), anyBoolean());
	}

	@Test
	void paginatesOldestFirstWithinPageWithExclusiveStableCursor() throws Exception {
		UUID id = completed("system");
		for (int index = 1; index <= 5; index++) {
			historyService.save(id, "system", "q" + index, answer("q" + index, "answered"));
		}
		JsonNode first = history(id, null, "2");
		assertQuestions(first, "q4", "q5");
		String cursor = first.get("nextCursor").asString();
		assertThat(cursor).isEqualTo(first.get("items").get(0).get("id").asString());

		// A new completed answer does not shift older pages or duplicate an already displayed turn.
		historyService.save(id, "system", "q6", answer("q6", "answered"));
		JsonNode second = history(id, cursor, "2");
		assertQuestions(second, "q2", "q3");
		JsonNode third = history(id, second.get("nextCursor").asString(), "2");
		assertQuestions(third, "q1");
		assertThat(third.get("nextCursor").isNull()).isTrue();
		assertThat(history(id, "1", "2").get("items").size()).isZero();
	}

	@Test
	void defaultsToThirtyAndDoesNotInventCursorForExactPage() throws Exception {
		UUID id = completed("system");
		for (int index = 1; index <= 31; index++) {
			historyService.save(id, "system", "q" + index, answer("q" + index, "answered"));
		}
		JsonNode page = history(id, null, null);
		assertThat(page.get("items").size()).isEqualTo(30);
		assertThat(page.get("nextCursor").isString()).isTrue();
		assertThat(history(id, null, "31").get("nextCursor").isNull()).isTrue();
	}

	@Test
	void deletesQuestionHistoryWithItsAnalysis() throws Exception {
		UUID id = completed("system");
		UUID other = completed("system");
		historyService.save(id, "system", "delete", answer("delete", "answered"));
		historyService.save(other, "system", "keep", answer("keep", "answered"));
		mockMvc.perform(delete("/api/v1/analyses/{id}", id)).andExpect(status().isNoContent());
		assertThat(questionRepository.count()).isEqualTo(1);
		assertQuestions(history(other, null, null), "keep");
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", id)).andExpect(status().isNotFound());
	}

	@Test
	void doesNotSaveAiFailuresOrTheirInternalDetails() throws Exception {
		UUID id = completed("system");
		when(aiServiceClient.askWorkbook(any(Resource.class), any(), anyBoolean()))
				.thenThrow(new AiServiceUnavailableException(new IllegalStateException("private-api-key")));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"실패\"}"))
				.andExpect(status().isServiceUnavailable());
		assertThat(questionRepository.count()).isZero();
	}

	@Test
	void neverHoldsTransactionDuringAiAndRechecksDeletionBeforeSaving() throws Exception {
		UUID id = completed("system");
		when(aiServiceClient.askWorkbook(any(Resource.class), any(), anyBoolean())).thenAnswer(invocation -> {
			assertThat(TransactionSynchronizationManager.isActualTransactionActive()).isFalse();
			analysisJobRepository.deleteById(id);
			return answer("응답 중 삭제", "answered");
		});
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content("{\"question\":\"응답 중 삭제\"}"))
				.andExpect(status().isNotFound());
		assertThat(questionRepository.count()).isZero();
	}

	@ParameterizedTest
	@CsvSource({"before,0", "before,-1", "before,abc", "before,9223372036854775808",
			"size,0", "size,-1", "size,101", "size,abc"})
	void rejectsInvalidPagination(String parameter, String value) throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{id}/questions", UUID.randomUUID()).param(parameter, value))
				.andExpect(status().isBadRequest());
	}

	private UUID completed(String owner) {
		Instant now = Instant.now();
		UUID id = UUID.randomUUID();
		AnalysisJob job = AnalysisJob.queued(id, AnalysisMode.BFS, "history.xlsx", "xlsx", 100, owner, false, now);
		job.markProcessing(now);
		job.markCompleted(now);
		analysisJobRepository.saveAndFlush(job);
		analysisFileStorage.store(id, "xlsx", excel("history.xlsx"));
		return id;
	}

	private JsonNode history(UUID id, String before, String size) throws Exception {
		var request = get("/api/v1/analyses/{id}/questions", id);
		if (before != null) request.param("before", before);
		if (size != null) request.param("size", size);
		return objectMapper.readTree(mockMvc.perform(request).andExpect(status().isOk())
				.andReturn().getResponse().getContentAsString());
	}

	private void assertQuestions(JsonNode page, String... expected) {
		List<String> questions = page.get("items").valueStream()
				.map(item -> item.get("answer").get("question").asString()).toList();
		assertThat(questions).containsExactly(expected);
	}

	private AiWorkbookQuestion answer(String question, String status) {
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
