package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.http.MediaType;
import tools.jackson.databind.json.JsonMapper;

class WorkbookClarificationValidationTests extends AnalysisControllerTestSupport {
	@ParameterizedTest
	@MethodSource("invalidSelections")
	void rejectsMalformedSelectionsBeforeAiRequest(Object selection) throws Exception {
		String request = JsonMapper.builder().build().writeValueAsString(Map.of(
				"question", "선택한 매출 합계는?", "context", Map.of("selection", selection)));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", UUID.randomUUID())
				.contentType(MediaType.APPLICATION_JSON).content(request))
				.andExpect(status().isBadRequest());
		verifyNoInteractions(aiServiceClient);
	}

	static Stream<Object> invalidSelections() {
		return Stream.of("not an object", Map.of(),
				Map.of("source_question", "매출 합계는?"),
				Map.of("option_id", "a".repeat(64)),
				Map.of("source_question", " ", "option_id", "a".repeat(64)),
				Map.of("source_question", "a", "option_id", "a".repeat(64)),
				Map.of("source_question", "a".repeat(1001), "option_id", "a".repeat(64)),
				Map.of("source_question", "매출 합계는?", "option_id", "a".repeat(63)),
				Map.of("source_question", "매출 합계는?", "option_id", "a".repeat(65)),
				Map.of("source_question", "매출 합계는?", "option_id", "A".repeat(64)),
				Map.of("source_question", "매출 합계는?", "option_id", "g".repeat(64)));
	}
}
