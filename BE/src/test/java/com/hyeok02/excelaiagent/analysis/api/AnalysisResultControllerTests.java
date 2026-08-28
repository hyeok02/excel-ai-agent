package com.hyeok02.excelaiagent.analysis.api;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;
import com.hyeok02.excelaiagent.analysis.domain.*;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

class AnalysisResultControllerTests extends AnalysisControllerTestSupport {
	@Test
	void returnsStoredAnalysisResult() throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("sales.xlsx")).param("mode", "BFS"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(body, "$.analysisId");
		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.workbook.filename").value("sales.xlsx"))
				.andExpect(jsonPath("$.workbook.totalSheetCount").value(2))
				.andExpect(jsonPath("$.workbook.excludedSheets[0].analysisInclusion.decision").value("exclude"))
				.andExpect(jsonPath("$.workbook.sheets[0].sheetClassification.role").value("output"))
				.andExpect(jsonPath("$.workbook.sheets[0].columnSchemas[0].standardField")
						.value("revenue"))
				.andExpect(jsonPath("$.workbook.sheets[0].columnSchemas[0].provenance.evidence[0].reference")
						.value("A1:D3"))
				.andExpect(jsonPath("$.workbook.sheets[0].formulas[0].provenance.analyzer")
						.value("formula_parser"))
				.andExpect(jsonPath("$.workbook.sheets[0].formulas[0].provenance.evidence[0].sheetName")
						.value("Sales"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].semantic.role").value("data"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].previewRows[0][0].semantic.role")
						.value("header"))
				.andExpect(jsonPath("$.workbook.sheets[0].charts[0].series[0].valueSamples[0]").value(10))
				.andExpect(jsonPath("$.workbook.dependencyGraph.cycleCount").value(1))
				.andExpect(jsonPath("$.workbook.dependencyGraph.clusters[0].edges[0].target")
						.value("Sales!D2"))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.totalCount").value(1))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.findings[0].kind")
						.value("external_reference"))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.highRiskCount").value(1))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.findings[0].impact.riskScore")
						.value(62))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.findings[0].impact.affectedFormulaCount")
						.value(2))
				.andExpect(jsonPath("$.workbook.formulaRiskSummary.findings[0].provenance.evidence[0].sheetName")
						.value("Sales"));
	}

	@Test
	void returnsGeneratedInsightsForLlmAnalysis() throws Exception {
		String body = mockMvc.perform(multipart("/api/v1/analyses")
					.file(excel("sales.xlsx")).param("mode", "LLM"))
				.andReturn().getResponse().getContentAsString();
		String id = JsonPath.read(body, "$.analysisId");
		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.insightReport.overview").value("수식 구조를 검토했습니다."))
				.andExpect(jsonPath("$.insightReport.insights[0].category").value("formula"))
				.andExpect(jsonPath("$.insightReport.insights[0].evidence[0]").value("Sales!D2"));
	}

	@Test
	void returnsLegacyWorkbookSummaryResult() throws Exception {
		UUID id = UUID.randomUUID();
		Instant now = Instant.now();
		analysisJobRepository.save(AnalysisJob.queued(id, AnalysisMode.BFS, "legacy.xlsx", "xlsx", 100L, now));
		analysisResultRepository.save(AnalysisResult.completed(id,
				"{\"filename\":\"legacy.xlsx\",\"sheet_count\":1,\"sheets\":[]}", now));
		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", id))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.workbook.filename").value("legacy.xlsx"))
				.andExpect(jsonPath("$.insightReport").doesNotExist());
	}

	@Test
	void returnsConflictWhenAnalysisResultIsNotReady() throws Exception {
		AnalysisJob job = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "queued.xlsx", "xlsx", 100L, Instant.now());
		analysisJobRepository.save(job);
		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", job.getAnalysisId()))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("ANALYSIS_RESULT_NOT_READY"));
	}

	@Test
	void returnsNotFoundForUnknownAnalysisResult() throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", UUID.randomUUID()))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
	}
}
