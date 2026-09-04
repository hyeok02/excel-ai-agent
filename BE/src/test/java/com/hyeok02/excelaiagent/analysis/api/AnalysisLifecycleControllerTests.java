package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.*;
import com.hyeok02.excelaiagent.analysis.error.UnreadableExcelFileException;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.springframework.core.io.Resource;

class AnalysisLifecycleControllerTests extends AnalysisControllerTestSupport {
	@Test
	void returnsNotFoundForUnknownAnalysisId() throws Exception {
		UUID id = UUID.randomUUID();
		mockMvc.perform(get("/api/v1/analyses/{analysisId}", id))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
	}

	@Test
	void deletesAnalysisById() throws Exception {
		AnalysisJob job = analysisJobRepository.save(AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales.xlsx", "xlsx", 100L,
				"system", Instant.now()));
		mockMvc.perform(delete("/api/v1/analyses/{analysisId}", job.getAnalysisId()))
				.andExpect(status().isNoContent());
		mockMvc.perform(get("/api/v1/analyses/{analysisId}", job.getAnalysisId()))
				.andExpect(status().isNotFound());
	}

	@Test
	void returnsNotFoundWhenDeletingUnknownAnalysisId() throws Exception {
		mockMvc.perform(delete("/api/v1/analyses/{analysisId}", UUID.randomUUID()))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
	}

	@Test
	void rejectsMalformedAnalysisId() throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{analysisId}", "not-a-uuid"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_ID"));
	}

	@Test
	void savesFailedStatusWhenAiServiceCannotAnalyzeWorkbook() throws Exception {
		when(aiServiceClient.summarizeWorkbook(any(Resource.class)))
				.thenThrow(new AiServiceUnavailableException());
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("sales.xlsx")).param("mode", "BFS"))
				.andExpect(status().isAccepted());
		assertThat(analysisJobRepository.findAll()).singleElement().satisfies(job ->
				assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED));
		assertThat(analysisResultRepository.findAll()).isEmpty();
	}

	@Test
	void savesFailedStatusWhenInsightGenerationFails() throws Exception {
		when(aiServiceClient.generateWorkbookInsights(any(Resource.class), any()))
				.thenThrow(new AiServiceUnavailableException());
		mockMvc.perform(multipart("/api/v1/analyses").file(excel("sales.xlsx")).param("mode", "LLM"))
				.andExpect(status().isAccepted());
		assertThat(analysisJobRepository.findAll()).singleElement().satisfies(job ->
				assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED));
		assertThat(analysisResultRepository.findAll()).isEmpty();
	}

	@ParameterizedTest
	@EnumSource(AnalysisMode.class)
	void persistsSafeFileErrorForStatusAndHistoryAfterAsyncFailure(AnalysisMode mode) throws Exception {
		when(aiServiceClient.summarizeWorkbook(any(Resource.class)))
				.thenThrow(new UnreadableExcelFileException());
		when(aiServiceClient.generateWorkbookInsights(any(Resource.class), any()))
				.thenThrow(new UnreadableExcelFileException());
		String response = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("styles.xlsx")).param("mode", mode.name()))
				.andExpect(status().isAccepted())
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(response, "$.analysisId");

		assertThat(analysisJobRepository.findById(UUID.fromString(id))).get().satisfies(job -> {
			assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED);
			assertThat(job.getFailureMessage()).isEqualTo(UnreadableExcelFileException.STYLE_MESSAGE);
		});
		mockMvc.perform(get("/api/v1/analyses/{id}", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.failureMessage").value(UnreadableExcelFileException.STYLE_MESSAGE));
		mockMvc.perform(get("/api/v1/analyses"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].failureMessage")
						.value(UnreadableExcelFileException.STYLE_MESSAGE));
		assertThat(analysisResultRepository.findAll()).isEmpty();
	}

	@Test
	void doesNotPersistUnexpectedExceptionDetails() throws Exception {
		when(aiServiceClient.summarizeWorkbook(any(Resource.class)))
				.thenThrow(new RuntimeException("private api_key=secret /srv/uploads/file.xlsx"));
		String response = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("failed.xlsx")).param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(response, "$.analysisId");

		assertThat(analysisJobRepository.findById(UUID.fromString(id))).get().satisfies(job -> {
			assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED);
			assertThat(job.getFailureMessage()).isNull();
		});
		mockMvc.perform(get("/api/v1/analyses/{id}", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.failureMessage").doesNotExist());
	}

	@Test
	void returnsLegacyFailedRecordWithoutSpecificMessage() throws Exception {
		AnalysisJob job = AnalysisJob.queued(UUID.randomUUID(), AnalysisMode.BFS,
				"legacy.xlsx", "xlsx", 100, "system", Instant.now());
		job.markProcessing(Instant.now());
		job.markFailed(Instant.now());
		analysisJobRepository.saveAndFlush(job);

		mockMvc.perform(get("/api/v1/analyses/{id}", job.getAnalysisId()))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("FAILED"))
				.andExpect(jsonPath("$.failureMessage").doesNotExist());
	}
}
