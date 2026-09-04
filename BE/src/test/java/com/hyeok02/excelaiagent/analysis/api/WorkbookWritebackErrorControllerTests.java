package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hyeok02.excelaiagent.analysis.error.UnreadableExcelFileException;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class WorkbookWritebackErrorControllerTests extends WorkbookWritebackTestSupport {

	@Test
	void returnsSafeFileErrorForWritebackProposal() throws Exception {
		when(aiWritebackClient.propose(any(), anyString()))
				.thenThrow(new UnreadableExcelFileException());
		String analysisId = submitCompleted();

		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_EXCEL_FILE"))
				.andExpect(jsonPath("$.message").value(UnreadableExcelFileException.STYLE_MESSAGE));
	}

	@Test
	void keepsApprovalPendingWhenTheOriginalCannotBeRead() throws Exception {
		when(aiWritebackClient.propose(any(), anyString())).thenReturn(proposal(false));
		when(aiWritebackClient.apply(any(), any())).thenThrow(new UnreadableExcelFileException());
		String analysisId = submitCompleted();
		String response = mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andReturn().getResponse().getContentAsString();
		String writebackId = JsonPath.read(response, "$.writebackId");

		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks/{wid}/approve", analysisId, writebackId)
					.contentType(MediaType.APPLICATION_JSON).content("{\"confirmed\":true}"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_EXCEL_FILE"))
				.andExpect(jsonPath("$.message").value(UnreadableExcelFileException.STYLE_MESSAGE));
		mockMvc.perform(get("/api/v1/analyses/{id}/writebacks", analysisId))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$[0].status").value("PROPOSED"))
				.andExpect(jsonPath("$[0].downloadable").value(false));
	}

	@Test
	void keepsWritebackOutagesUnavailable() throws Exception {
		when(aiWritebackClient.propose(any(), anyString()))
				.thenThrow(new AiServiceUnavailableException(new RuntimeException("private detail")));
		String analysisId = submitCompleted();

		mockMvc.perform(post("/api/v1/analyses/{id}/writebacks", analysisId)
					.contentType(MediaType.APPLICATION_JSON)
					.content("{\"instruction\":\"B2를 12로 수정해줘\"}"))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"))
				.andExpect(jsonPath("$.message")
						.value("AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요."));
	}
}
