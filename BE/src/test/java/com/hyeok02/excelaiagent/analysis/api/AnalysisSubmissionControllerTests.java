package com.hyeok02.excelaiagent.analysis.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;

class AnalysisSubmissionControllerTests extends AnalysisControllerTestSupport {
	@Test
	void acceptsValidExcelAnalysisRequest() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("sales.xlsx")).param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.analysisId").isNotEmpty())
				.andExpect(jsonPath("$.status").value("QUEUED"))
				.andExpect(jsonPath("$.mode").value("BFS"))
				.andExpect(jsonPath("$.originalFilename").value("sales.xlsx"))
				.andExpect(jsonPath("$.sizeBytes").value(ZIP_FILE.length));
	}

	@Test
	void rejectsUnsupportedFile() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "sales.csv", "text/csv", ZIP_FILE);
		mockMvc.perform(multipart("/api/v1/analyses").file(file).param("mode", "BFS"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_EXCEL_FILE"));
	}

	@Test
	void rejectsUnknownAnalysisMode() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("sales.xlsx")).param("mode", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_MODE"));
	}

	@Test
	void forwardsRequestedAnalysisDepthToAiService() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("finance.xlsx"))
					.param("mode", "LLM").param("depth", "PRECISE"))
				.andExpect(status().isAccepted());
		verify(aiServiceClient).generateWorkbookInsights(any(Resource.class), eq(AnalysisDepth.PRECISE));
	}

	@Test
	void rejectsUnknownAnalysisDepth() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("finance.xlsx"))
					.param("mode", "LLM").param("depth", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_DEPTH"));
	}

	@Test
	void rejectsRequestWithoutFile() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses").param("mode", "LLM"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("MISSING_REQUEST_VALUE"));
	}

	@Test
	void returnsSavedAnalysisById() throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("finance.xlsm")).param("mode", "LLM"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(body, "$.analysisId");
		mockMvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders
					.get("/api/v1/analyses/{analysisId}", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("COMPLETED"))
				.andExpect(jsonPath("$.originalFilename").value("finance.xlsm"));
	}
}
