package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import tools.jackson.databind.JsonNode;

class WorkbookQuestionHistoryControllerTests extends WorkbookQuestionHistoryTestSupport {

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

}
