package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
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
import com.hyeok02.excelaiagent.integration.ai.WorkbookQuestionContext;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import tools.jackson.databind.json.JsonMapper;

class WorkbookQuestionContextControllerTests extends AnalysisControllerTestSupport {
	private static final String REQUEST = """
			{"question":"그럼 2월은?","context":{
			 "turns":[{"question":"노트북의 1월 값은?","evidence":["매출현황!B2"],
			           "needs_clarification":true,"answer":"untrusted answer","facts":["fake fact"]}],
			 "insights":[{"title":"월별 매출","topic":"노트북","evidence":["매출현황!A1:C3"],
			              "description":"untrusted narrative"}],"answer":"fake answer"}}
			""";

	@Test
	void forwardsOnlyQuestionAndSourceHintsAndKeepsHiddenSheetPolicy() throws Exception {
		var response = new AiWorkbookQuestion("그럼 2월은?", "20입니다.", "answered", 1,
				List.of(), List.of(), List.of(), null, "노트북의 2월 값은?");
		when(aiServiceClient.askWorkbook(any(Resource.class), eq("그럼 2월은?"), eq(true), any()))
				.thenReturn(response);
		String submission = mockMvc.perform(multipart("/api/v1/analyses")
				.file(excel("sales.xlsx")).param("mode", "BFS").param("includeHiddenSheets", "true"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(submission, "$.analysisId");

		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content(REQUEST))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.resolvedQuestion").value("노트북의 2월 값은?"));

		var context = ArgumentCaptor.forClass(WorkbookQuestionContext.class);
		verify(aiServiceClient).askWorkbook(any(Resource.class), eq("그럼 2월은?"), eq(true), context.capture());
		assertThat(context.getValue().turns()).singleElement().satisfies(turn -> {
			assertThat(turn.question()).isEqualTo("노트북의 1월 값은?");
			assertThat(turn.evidence()).containsExactly("매출현황!B2");
			assertThat(turn.needsClarification()).isTrue();
		});
		assertThat(context.getValue().insights()).singleElement().satisfies(insight ->
				assertThat(insight.topic()).isEqualTo("노트북"));
		assertThat(JsonMapper.builder().build().writeValueAsString(context.getValue()))
				.contains("\"needs_clarification\":true")
				.doesNotContain("answer", "facts", "description", "untrusted", "fake");
	}

	@Test
	void olderContextWithoutClarificationFlagDefaultsToFalse() {
		var mapper = JsonMapper.builder().build();
		var context = mapper.readValue("""
				{"turns":[{"question":"기존 질문","evidence":["Data!A1"]}]}
				""", WorkbookQuestionContext.class);
		assertThat(context.turns().getFirst().needsClarification()).isFalse();
		assertThat(mapper.writeValueAsString(context)).contains("\"needs_clarification\":false");
	}

	@Test
	void contextCannotAccessAnotherOwnersWorkbook() throws Exception {
		AnalysisJob foreign = analysisJobRepository.save(AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "private.xlsx", "xlsx", 100,
				"another-user", true, Instant.now()));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", foreign.getAnalysisId())
				.contentType(MediaType.APPLICATION_JSON).content(REQUEST))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
		verifyNoInteractions(aiServiceClient);
	}

	@Test
	void contextCannotReplaceAnExpiredSource() throws Exception {
		String submission = mockMvc.perform(multipart("/api/v1/analyses")
				.file(excel("sales.xlsx")).param("mode", "BFS"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(submission, "$.analysisId");
		analysisFileStorage.delete(UUID.fromString(id));
		mockMvc.perform(post("/api/v1/analyses/{id}/questions", id)
				.contentType(MediaType.APPLICATION_JSON).content(REQUEST))
				.andExpect(status().isGone())
				.andExpect(jsonPath("$.code").value("ANALYSIS_SOURCE_UNAVAILABLE"));
	}
}
