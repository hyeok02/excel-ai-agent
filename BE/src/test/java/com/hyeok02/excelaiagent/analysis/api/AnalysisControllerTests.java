package com.hyeok02.excelaiagent.analysis.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;

import com.jayway.jsonpath.JsonPath;
import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockMultipartFile;
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

	@BeforeEach
	void clearAnalysisJobs() {
		analysisJobRepository.deleteAll();
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
				.andExpect(jsonPath("$.status").value("QUEUED"))
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
				.andExpect(jsonPath("$.status").value("QUEUED"))
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
	void returnsNotFoundForUnknownAnalysisId() throws Exception {
		UUID unknownId = UUID.randomUUID();

		mockMvc.perform(get("/api/v1/analyses/{analysisId}", unknownId))
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
}
