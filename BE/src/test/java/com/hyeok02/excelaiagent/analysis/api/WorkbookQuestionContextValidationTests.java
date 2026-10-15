package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.http.MediaType;
import tools.jackson.databind.json.JsonMapper;

class WorkbookQuestionContextValidationTests extends AnalysisControllerTestSupport {
	@ParameterizedTest
	@MethodSource("invalidContexts")
	void rejectsMalformedOrOversizedContextBeforeAiRequest(Object context) throws Exception {
		String request = JsonMapper.builder().build().writeValueAsString(
				Map.of("question", "그중 두 번째는?", "context", context));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", UUID.randomUUID())
				.contentType(MediaType.APPLICATION_JSON).content(request))
				.andExpect(status().isBadRequest());
		verifyNoInteractions(aiServiceClient);
	}

	static Stream<Object> invalidContexts() {
		var turn = Map.of("question", "이전 질문", "evidence", List.of("Sheet1!A1"));
		var insight = Map.of("title", "항목", "evidence", List.of("Sheet1!A1"));
		return Stream.of(
				"not an object",
				Map.of("turns", Map.of("question", "not a list")),
				Map.of("turns", Collections.nCopies(7, turn)),
				Map.of("insights", Collections.nCopies(7, insight)),
				Map.of("turns", Collections.singletonList(null)),
				Map.of("insights", Collections.singletonList(null)),
				Map.of("turns", List.of(Map.of("question", " ", "evidence", List.of()))),
				Map.of("turns", List.of(Map.of("question", "a".repeat(1001), "evidence", List.of()))),
				Map.of("turns", List.of(Map.of("question", "이전 질문"))),
				Map.of("turns", List.of(Map.of("question", "이전 질문", "evidence", Collections.nCopies(13, "S!A1")))),
				Map.of("turns", List.of(Map.of("question", "이전 질문", "evidence", List.of("x".repeat(201))))),
				Map.of("turns", List.of(Map.of("question", "이전 질문", "evidence", Collections.singletonList(null)))),
				Map.of("insights", List.of(Map.of("title", "x".repeat(201), "evidence", List.of()))),
				Map.of("insights", List.of(Map.of("title", "항목", "topic", "x".repeat(201), "evidence", List.of()))),
				Map.of("insights", List.of(Map.of("title", "항목", "evidence", Collections.nCopies(13, "S!A1")))),
				Map.of("insights", List.of(Map.of("title", "항목", "evidence", List.of(" ")))));
	}
}
