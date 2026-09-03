package com.hyeok02.excelaiagent.analysis.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;
import com.jayway.jsonpath.JsonPath;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import org.junit.jupiter.api.Test;

class AnalysisHistoryControllerTests extends AnalysisControllerTestSupport {
	@Test
	void returnsAnalysisHistoryNewestFirstWithPagination() throws Exception {
		Instant now = Instant.now();
		analysisJobRepository.save(job("older.xlsx", AnalysisMode.BFS, now.minusSeconds(60)));
		AnalysisJob newer = analysisJobRepository.save(job("newer.xlsm", AnalysisMode.LLM, now));
		mockMvc.perform(get("/api/v1/analyses").param("page", "0").param("size", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(newer.getAnalysisId().toString()))
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
		AnalysisJob bfs = analysisJobRepository.save(job("sales.xlsx", AnalysisMode.BFS, now));
		analysisJobRepository.save(job("finance.xlsx", AnalysisMode.LLM, now.minusSeconds(1)));
		mockMvc.perform(get("/api/v1/analyses").param("mode", "BFS"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(bfs.getAnalysisId().toString()))
				.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	void filtersAnalysisHistoryByTrimmedFilenameIgnoringCase() throws Exception {
		Instant now = Instant.now();
		AnalysisJob match = analysisJobRepository.save(job("Monthly_SALES.xlsx", AnalysisMode.BFS, now));
		analysisJobRepository.save(job("inventory.xlsx", AnalysisMode.BFS, now.minusSeconds(1)));
		mockMvc.perform(get("/api/v1/analyses").param("filename", "  sales  "))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(match.getAnalysisId().toString()))
				.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	void ignoresBlankFilenameFilter() throws Exception {
		AnalysisJob saved = analysisJobRepository.save(job("sales.xlsx", AnalysisMode.BFS, Instant.now()));
		mockMvc.perform(get("/api/v1/analyses").param("filename", "   "))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(saved.getAnalysisId().toString()));
	}

	@Test
	void combinesModeAndFilenameFiltersWithPagination() throws Exception {
		Instant now = Instant.now();
		analysisJobRepository.save(job("sales-old.xlsx", AnalysisMode.BFS, now.minusSeconds(2)));
		AnalysisJob newest = analysisJobRepository.save(job("sales-new.xlsx", AnalysisMode.BFS, now));
		analysisJobRepository.save(job("sales-llm.xlsx", AnalysisMode.LLM, now.minusSeconds(1)));
		mockMvc.perform(get("/api/v1/analyses").param("mode", "BFS")
					.param("filename", "sales").param("page", "0").param("size", "1"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(newest.getAnalysisId().toString()))
				.andExpect(jsonPath("$.totalElements").value(2));
	}

	@Test
	void rejectsUnknownAnalysisHistoryMode() throws Exception {
		mockMvc.perform(get("/api/v1/analyses").param("mode", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_MODE"));
	}

	@Test
	void returnsOnlyTheSignedInUsersAnalysisHistory() throws Exception {
		AnalysisJob mine = analysisJobRepository.save(job(
				"mine.xlsx", AnalysisMode.BFS, "alice", Instant.now()));
		analysisJobRepository.save(job(
				"other.xlsx", AnalysisMode.LLM, "bob", Instant.now().minusSeconds(1)));

		mockMvc.perform(get("/api/v1/analyses").with(user("alice")))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.totalElements").value(1))
				.andExpect(jsonPath("$.content[0].analysisId")
						.value(mine.getAnalysisId().toString()))
				.andExpect(jsonPath("$.content[0].originalFilename").value("mine.xlsx"));
	}

	@Test
	void marksHistoryWhenTheOriginalFileHasExpired() throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("expired.xlsx")).param("mode", "BFS"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(body, "$.analysisId");
		analysisFileStorage.delete(UUID.fromString(id));

		mockMvc.perform(get("/api/v1/analyses"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.content[0].analysisId").value(id))
				.andExpect(jsonPath("$.content[0].sourceAvailable").value(false));
	}

	private AnalysisJob job(String filename, AnalysisMode mode, Instant createdAt) {
		return job(filename, mode, "system", createdAt);
	}

	private AnalysisJob job(
			String filename, AnalysisMode mode, String ownerUsername, Instant createdAt) {
		return AnalysisJob.queued(UUID.randomUUID(), mode, filename,
				filename.endsWith("xlsm") ? "xlsm" : "xlsx", 100L,
				ownerUsername, createdAt);
	}
}
