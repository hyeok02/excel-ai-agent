package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookQuestion;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;

class WorkbookQuestionControllerTests extends AnalysisControllerTestSupport {
	@Test
	void asksQuestionAgainstStoredAnalysisSource() throws Exception {
		when(aiServiceClient.askWorkbook(any(Resource.class), eq("노트북의 1월 값은 얼마야?")))
				.thenReturn(answer());
		String submission = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("sales.xlsx")).param("mode", "BFS"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(submission, "$.analysisId");

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/questions", id)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"question\":\"노트북의 1월 값은 얼마야?\"}"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("answered"))
				.andExpect(jsonPath("$.selectedTools[0]").value("search_workbook_data"))
				.andExpect(jsonPath("$.evidence[0].sheetName").value("매출현황"))
				.andExpect(jsonPath("$.evidence[0].reference").value("B2"))
				.andExpect(jsonPath("$.evidence[0].value").value(10));

		verify(aiServiceClient).askWorkbook(any(Resource.class), eq("노트북의 1월 값은 얼마야?"));
	}

	@Test
	void rejectsBlankQuestion() throws Exception {
		mockMvc.perform(post("/api/v1/analyses/{analysisId}/questions", UUID.randomUUID())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"question\":\" \"}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	@Test
	void rejectsQuestionBeforeAnalysisCompletes() throws Exception {
		AnalysisJob queued = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "queued.xlsx", "xlsx", 100,
				"system", Instant.now());
		analysisJobRepository.save(queued);

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/questions", queued.getAnalysisId())
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"question\":\"핵심 내용을 알려줘\"}"))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("ANALYSIS_RESULT_NOT_READY"));
	}

	@Test
	void returnsGoneWhenOriginalFileHasExpired() throws Exception {
		String submission = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("expired.xlsx")).param("mode", "BFS"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(submission, "$.analysisId");
		analysisFileStorage.delete(UUID.fromString(id));

		mockMvc.perform(post("/api/v1/analyses/{analysisId}/questions", id)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"question\":\"핵심 내용을 알려줘\"}"))
				.andExpect(status().isGone())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SOURCE_UNAVAILABLE"));
	}

	private AiWorkbookQuestion answer() {
		return new AiWorkbookQuestion(
				"노트북의 1월 값은 얼마야?", "노트북의 1월 값은 10입니다.",
				"answered", 0.94, List.of("search_workbook_data"),
				List.of(new AiWorkbookQuestion.Evidence(
						"cell", "매출현황", "B2", "원본 셀", 10, null, "10")),
				List.of());
	}
}
