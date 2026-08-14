package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.jayway.jsonpath.JsonPath;
import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(
		classes = BackendApplication.class,
		properties = "app.storage.upload-dir=build/test-uploads")
@AutoConfigureMockMvc
class AnalysisControllerTests {

	private static final byte[] ZIP_FILE = {0x50, 0x4b, 0x03, 0x04, 0x01};

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private AnalysisJobRepository analysisJobRepository;

	@MockitoBean
	private AiServiceClient aiServiceClient;

	@BeforeEach
	void clearAnalysisJobs() {
		analysisJobRepository.deleteAll();
		reset(aiServiceClient);
		when(aiServiceClient.summarizeWorkbook(any())).thenReturn(workbookSummary());
	}

	@Test
	void acceptsValidExcelAnalysisRequest() throws Exception {
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.analysisId").isNotEmpty())
				.andExpect(jsonPath("$.status").value("COMPLETED"))
				.andExpect(jsonPath("$.mode").value("BFS"))
				.andExpect(jsonPath("$.originalFilename").value("sales.xlsx"))
				.andExpect(jsonPath("$.sizeBytes").value(ZIP_FILE.length))
				.andExpect(jsonPath("$.createdAt").isNotEmpty());
	}

	@Test
	void rejectsUnsupportedFile() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "sales.csv", "text/csv", ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "BFS"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_EXCEL_FILE"))
				.andExpect(jsonPath("$.message").value(".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다."));
	}

	@Test
	void rejectsUnknownAnalysisMode() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "sales.xlsx", null, ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_MODE"))
				.andExpect(jsonPath("$.message").value("mode는 BFS 또는 LLM 중 하나여야 합니다."));
	}

	@Test
	void rejectsRequestWithoutFile() throws Exception {
		mockMvc.perform(multipart("/api/v1/analyses")
					.param("mode", "LLM"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("MISSING_REQUEST_VALUE"));
	}

	@Test
	void returnsSavedAnalysisById() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "finance.xlsm", null, ZIP_FILE);
		String submissionBody = mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "LLM"))
				.andExpect(status().isAccepted())
				.andReturn()
				.getResponse()
				.getContentAsString();
		String analysisId = JsonPath.read(submissionBody, "$.analysisId");

		mockMvc.perform(get("/api/v1/analyses/{analysisId}", analysisId))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.analysisId").value(analysisId))
				.andExpect(jsonPath("$.status").value("COMPLETED"))
				.andExpect(jsonPath("$.mode").value("LLM"))
				.andExpect(jsonPath("$.originalFilename").value("finance.xlsm"))
				.andExpect(jsonPath("$.fileExtension").value("xlsm"))
				.andExpect(jsonPath("$.sizeBytes").value(ZIP_FILE.length))
				.andExpect(jsonPath("$.createdAt").isNotEmpty())
				.andExpect(jsonPath("$.updatedAt").isNotEmpty());
	}

	@Test
	void returnsAnalysisHistoryNewestFirstWithPagination() throws Exception {
		Instant now = Instant.now();
		AnalysisJob older = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "older.xlsx", "xlsx", 100L, now.minusSeconds(60));
		AnalysisJob newer = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.LLM, "newer.xlsm", "xlsm", 200L, now);
		analysisJobRepository.save(older);
		analysisJobRepository.save(newer);

		mockMvc.perform(get("/api/v1/analyses")
					.param("page", "0")
					.param("size", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].analysisId").value(newer.getAnalysisId().toString()))
				.andExpect(jsonPath("$.content[0].originalFilename").value("newer.xlsm"))
				.andExpect(jsonPath("$.page").value(0))
				.andExpect(jsonPath("$.size").value(1))
				.andExpect(jsonPath("$.totalElements").value(2))
				.andExpect(jsonPath("$.totalPages").value(2))
				.andExpect(jsonPath("$.hasNext").value(true));
	}

	@Test
	void rejectsInvalidAnalysisHistoryPageSize() throws Exception {
		mockMvc.perform(get("/api/v1/analyses").param("size", "0"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_PAGINATION"));
	}

	@Test
	void filtersAnalysisHistoryByMode() throws Exception {
		Instant now = Instant.now();
		AnalysisJob bfsJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales.xlsx", "xlsx", 100L, now);
		AnalysisJob llmJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.LLM, "finance.xlsx", "xlsx", 200L, now.minusSeconds(1));
		analysisJobRepository.save(bfsJob);
		analysisJobRepository.save(llmJob);

		mockMvc.perform(get("/api/v1/analyses").param("mode", "BFS"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].analysisId").value(bfsJob.getAnalysisId().toString()))
				.andExpect(jsonPath("$.content[0].mode").value("BFS"))
				.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	void filtersAnalysisHistoryByTrimmedFilenameIgnoringCase() throws Exception {
		Instant now = Instant.now();
		AnalysisJob matchingJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "Monthly_SALES.xlsx", "xlsx", 100L, now);
		AnalysisJob otherJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "inventory.xlsx", "xlsx", 200L, now.minusSeconds(1));
		analysisJobRepository.save(matchingJob);
		analysisJobRepository.save(otherJob);

		mockMvc.perform(get("/api/v1/analyses").param("filename", "  sales  "))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].analysisId").value(matchingJob.getAnalysisId().toString()))
				.andExpect(jsonPath("$.content[0].originalFilename").value("Monthly_SALES.xlsx"))
				.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	void ignoresBlankFilenameFilter() throws Exception {
		AnalysisJob analysisJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales.xlsx", "xlsx", 100L, Instant.now());
		analysisJobRepository.save(analysisJob);

		mockMvc.perform(get("/api/v1/analyses").param("filename", "   "))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].analysisId").value(analysisJob.getAnalysisId().toString()))
				.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	void combinesModeAndFilenameFiltersWithPagination() throws Exception {
		Instant now = Instant.now();
		AnalysisJob olderMatch = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales-old.xlsx", "xlsx", 100L, now.minusSeconds(2));
		AnalysisJob newerMatch = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales-new.xlsx", "xlsx", 200L, now);
		AnalysisJob wrongMode = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.LLM, "sales-llm.xlsx", "xlsx", 300L, now.minusSeconds(1));
		analysisJobRepository.save(olderMatch);
		analysisJobRepository.save(newerMatch);
		analysisJobRepository.save(wrongMode);

		mockMvc.perform(get("/api/v1/analyses")
					.param("mode", "BFS")
					.param("filename", "sales")
					.param("page", "0")
					.param("size", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content.length()").value(1))
				.andExpect(jsonPath("$.content[0].analysisId").value(newerMatch.getAnalysisId().toString()))
				.andExpect(jsonPath("$.totalElements").value(2))
				.andExpect(jsonPath("$.totalPages").value(2))
				.andExpect(jsonPath("$.hasNext").value(true));
	}

	@Test
	void rejectsUnknownAnalysisHistoryMode() throws Exception {
		mockMvc.perform(get("/api/v1/analyses").param("mode", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_MODE"))
				.andExpect(jsonPath("$.message").value("mode는 BFS 또는 LLM 중 하나여야 합니다."));
	}

	@Test
	void returnsNotFoundForUnknownAnalysisId() throws Exception {
		UUID unknownId = UUID.randomUUID();

		mockMvc.perform(get("/api/v1/analyses/{analysisId}", unknownId))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"))
				.andExpect(jsonPath("$.message").value("분석 작업을 찾을 수 없습니다: " + unknownId));
	}

	@Test
	void deletesAnalysisById() throws Exception {
		AnalysisJob analysisJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales.xlsx", "xlsx", 100L, Instant.now());
		analysisJobRepository.save(analysisJob);

		mockMvc.perform(delete("/api/v1/analyses/{analysisId}", analysisJob.getAnalysisId()))
				.andExpect(status().isNoContent());

		mockMvc.perform(get("/api/v1/analyses/{analysisId}", analysisJob.getAnalysisId()))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
	}

	@Test
	void returnsNotFoundWhenDeletingUnknownAnalysisId() throws Exception {
		UUID unknownId = UUID.randomUUID();

		mockMvc.perform(delete("/api/v1/analyses/{analysisId}", unknownId))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"))
				.andExpect(jsonPath("$.message").value("분석 작업을 찾을 수 없습니다: " + unknownId));
	}

	@Test
	void rejectsMalformedAnalysisId() throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{analysisId}", "not-a-uuid"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_ID"))
				.andExpect(jsonPath("$.message").value("analysisId는 UUID 형식이어야 합니다."));
	}

	@Test
	void savesFailedStatusWhenAiServiceCannotAnalyzeWorkbook() throws Exception {
		when(aiServiceClient.summarizeWorkbook(any()))
				.thenThrow(new AiServiceUnavailableException());
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "BFS"))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"));

		List<AnalysisJob> jobs = analysisJobRepository.findAll();
		assertThat(jobs).singleElement().satisfies(job ->
				assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED));
	}

	private AiWorkbookSummary workbookSummary() {
		return new AiWorkbookSummary("sales.xlsx", 1, List.of());
	}
}
