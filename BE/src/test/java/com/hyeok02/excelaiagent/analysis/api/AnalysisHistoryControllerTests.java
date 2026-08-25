package com.hyeok02.excelaiagent.analysis.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;
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

	private AnalysisJob job(String filename, AnalysisMode mode, Instant createdAt) {
		return AnalysisJob.queued(UUID.randomUUID(), mode, filename,
				filename.endsWith("xlsm") ? "xlsm" : "xlsx", 100L, createdAt);
	}
}
