package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
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
import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResult;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticClassification;
import com.hyeok02.excelaiagent.integration.ai.AiSemanticReason;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookInsights;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import com.hyeok02.excelaiagent.integration.ai.SemanticRole;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.core.io.Resource;
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

	@Autowired
	private AnalysisResultRepository analysisResultRepository;

	@MockitoBean
	private AiServiceClient aiServiceClient;

	@BeforeEach
	void clearAnalysisJobs() {
		analysisJobRepository.deleteAll();
		reset(aiServiceClient);
		when(aiServiceClient.summarizeWorkbook(any(Resource.class))).thenReturn(workbookSummary());
		when(aiServiceClient.generateWorkbookInsights(any(Resource.class), any())).thenReturn(workbookInsights());
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
	void forwardsRequestedAnalysisDepthToAiService() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "finance.xlsx", null, ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "LLM")
					.param("depth", "PRECISE"))
				.andExpect(status().isAccepted());

		verify(aiServiceClient).generateWorkbookInsights(any(Resource.class), eq(AnalysisDepth.PRECISE));
	}

	@Test
	void rejectsUnknownAnalysisDepth() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "finance.xlsx", null, ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "LLM")
					.param("depth", "UNKNOWN"))
				.andExpect(status().isBadRequest())
				.andExpect(jsonPath("$.code").value("INVALID_ANALYSIS_DEPTH"))
				.andExpect(jsonPath("$.message")
						.value("depth는 AUTO, FAST 또는 PRECISE 중 하나여야 합니다."));
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
	void returnsStoredAnalysisResult() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "sales.xlsx", null, ZIP_FILE);
		String submissionBody = mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andReturn()
				.getResponse()
				.getContentAsString();
		String analysisId = JsonPath.read(submissionBody, "$.analysisId");

		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", analysisId))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.analysisId").value(analysisId))
				.andExpect(jsonPath("$.createdAt").isNotEmpty())
				.andExpect(jsonPath("$.workbook.filename").value("sales.xlsx"))
				.andExpect(jsonPath("$.workbook.sheetCount").value(1))
				.andExpect(jsonPath("$.workbook.sheets[0].name").value("Sales"))
				.andExpect(jsonPath("$.workbook.sheets[0].formulas[0].cell").value("D2"))
				.andExpect(jsonPath("$.workbook.sheets[0].formulas[0].references[0]").value("B2:C2"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].startCell").value("A1"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].semantic.role").value("data"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].semantic.confidence").value(0.91))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].semantic.reasons[0].code")
						.value("tabular_values"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].previewRows[0][0].address").value("A1"))
				.andExpect(jsonPath("$.workbook.sheets[0].regions[0].previewRows[0][0].semantic.role")
						.value("header"))
				.andExpect(jsonPath("$.workbook.sheets[0].tables[0].reference").value("A1:D3"))
				.andExpect(jsonPath("$.workbook.sheets[0].charts[0].title").value("월별 매출"))
				.andExpect(jsonPath("$.workbook.sheets[0].charts[0].series[0].valueSamples[0]").value(10))
				.andExpect(jsonPath("$.workbook.dependencyGraph.edgeCount").value(1))
				.andExpect(jsonPath("$.workbook.dependencyGraph.cycleCount").value(1))
				.andExpect(jsonPath("$.workbook.dependencyGraph.cyclicNodeCount").value(1))
				.andExpect(jsonPath("$.workbook.dependencyGraph.cycles[0].nodes[0].id")
						.value("Sales!D2"))
				.andExpect(jsonPath("$.workbook.dependencyGraph.clusters[0].edges[0].source")
						.value("Sales!B2:C2"))
				.andExpect(jsonPath("$.workbook.dependencyGraph.clusters[0].edges[0].target")
						.value("Sales!D2"));
	}

	@Test
	void returnsGeneratedInsightsForLlmAnalysis() throws Exception {
		MockMultipartFile file = new MockMultipartFile("file", "sales.xlsx", null, ZIP_FILE);
		String submissionBody = mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "LLM"))
				.andExpect(status().isAccepted())
				.andReturn()
				.getResponse()
				.getContentAsString();
		String analysisId = JsonPath.read(submissionBody, "$.analysisId");

		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", analysisId))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.workbook.filename").value("sales.xlsx"))
				.andExpect(jsonPath("$.insightReport.overview").value("수식 구조를 검토했습니다."))
				.andExpect(jsonPath("$.insightReport.insights[0].title").value("수식 참조 확인"))
				.andExpect(jsonPath("$.insightReport.insights[0].category").value("formula"))
				.andExpect(jsonPath("$.insightReport.insights[0].severity").value("warning"))
				.andExpect(jsonPath("$.insightReport.insights[0].evidence[0]").value("Sales!D2"))
				.andExpect(jsonPath("$.insightReport.limitations[0]").value("실제 셀 값은 분석하지 않았습니다."));
	}

	@Test
	void returnsLegacyWorkbookSummaryResult() throws Exception {
		UUID analysisId = UUID.randomUUID();
		Instant now = Instant.now();
		analysisJobRepository.save(AnalysisJob.queued(
				analysisId, AnalysisMode.BFS, "legacy.xlsx", "xlsx", 100L, now));
		analysisResultRepository.save(AnalysisResult.completed(
				analysisId,
				"""
				{
				  "filename": "legacy.xlsx",
				  "sheet_count": 1,
				  "sheets": []
				}
				""",
				now));

		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", analysisId))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.workbook.filename").value("legacy.xlsx"))
				.andExpect(jsonPath("$.workbook.sheetCount").value(1))
				.andExpect(jsonPath("$.insightReport").doesNotExist());
	}

	@Test
	void returnsConflictWhenAnalysisResultIsNotReady() throws Exception {
		AnalysisJob queuedJob = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "queued.xlsx", "xlsx", 100L, Instant.now());
		analysisJobRepository.save(queuedJob);

		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", queuedJob.getAnalysisId()))
				.andExpect(status().isConflict())
				.andExpect(jsonPath("$.code").value("ANALYSIS_RESULT_NOT_READY"))
				.andExpect(jsonPath("$.message").value(
						"분석 결과가 아직 준비되지 않았습니다: %s (status=QUEUED)"
								.formatted(queuedJob.getAnalysisId())));
	}

	@Test
	void returnsNotFoundForUnknownAnalysisResult() throws Exception {
		UUID unknownId = UUID.randomUUID();

		mockMvc.perform(get("/api/v1/analyses/{analysisId}/result", unknownId))
				.andExpect(status().isNotFound())
				.andExpect(jsonPath("$.code").value("ANALYSIS_NOT_FOUND"));
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
		when(aiServiceClient.summarizeWorkbook(any(Resource.class)))
				.thenThrow(new AiServiceUnavailableException());
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.status").value("QUEUED"));

		List<AnalysisJob> jobs = analysisJobRepository.findAll();
		assertThat(jobs).singleElement().satisfies(job ->
				assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED));
		assertThat(analysisResultRepository.findAll()).isEmpty();
	}

	@Test
	void savesFailedStatusWhenInsightGenerationFails() throws Exception {
		when(aiServiceClient.generateWorkbookInsights(any(Resource.class), any()))
				.thenThrow(new AiServiceUnavailableException());
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				ZIP_FILE);

		mockMvc.perform(multipart("/api/v1/analyses")
					.file(file)
					.param("mode", "LLM"))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.status").value("QUEUED"));

		assertThat(analysisJobRepository.findAll()).singleElement().satisfies(job ->
				assertThat(job.getStatus()).isEqualTo(AnalysisStatus.FAILED));
		assertThat(analysisResultRepository.findAll()).isEmpty();
	}

	private AiWorkbookSummary workbookSummary() {
		return new AiWorkbookSummary(
				"sales.xlsx",
				1,
				List.of(new AiWorkbookSummary.SheetSummary(
						"Sales",
						3,
						4,
						1,
						0,
						1,
						List.of(new AiWorkbookSummary.FormulaAnalysis(
								"D2",
								"=SUM(B2:C2)",
								List.of("B2:C2"))),
						1,
						List.of(regionSummary()),
						List.of(new AiWorkbookSummary.TableSummary(
								"SalesTable",
								"SalesTable",
								"A1:D3",
								List.of("상품", "1월", "2월", "합계"),
								3,
								4,
								List.of(),
								false)),
						List.of(new AiWorkbookSummary.ChartSummary(
								"월별 매출",
								"BarChart",
								"F2",
								1,
								List.of(new AiWorkbookSummary.ChartSeriesSummary(
										"1월",
										"'Sales'!$A$2:$A$3",
										"'Sales'!$B$2:$B$3",
										List.of("노트북", "모니터"),
										List.of(10, 5))),
								false)))),
				new AiWorkbookSummary.DependencySummary(
						2,
						1,
						1,
						0,
						0,
						0,
						1,
						List.of(new AiWorkbookSummary.DependencyCluster(
								"cluster-1",
								2,
								1,
								1,
								List.of("Sales"),
								List.of(
										new AiWorkbookSummary.DependencyNode(
												"Sales!B2:C2", "Sales!B2:C2", "Sales", "B2:C2", "range", null),
										new AiWorkbookSummary.DependencyNode(
												"Sales!D2", "Sales!D2", "Sales", "D2", "formula", "=SUM(B2:C2)")),
								List.of(new AiWorkbookSummary.DependencyEdge(
										"Sales!B2:C2", "Sales!D2", "B2:C2", false)),
								false)),
						1,
						1,
						List.of(new AiWorkbookSummary.DependencyCycle(
								"cycle-1",
								1,
								1,
								List.of("Sales"),
								List.of(new AiWorkbookSummary.DependencyNode(
										"Sales!D2", "Sales!D2", "Sales", "D2", "formula", "=D2+1")),
								List.of(new AiWorkbookSummary.DependencyEdge(
										"Sales!D2", "Sales!D2", "D2", false)),
								false))));
	}

	private AiWorkbookSummary.CellRegion regionSummary() {
		return new AiWorkbookSummary.CellRegion(
				"A1",
				"D3",
				12,
				null,
				3,
				4,
				List.of(),
				List.of(),
				List.of(List.of(cellSnapshot())),
				false,
				new AiSemanticClassification(
						SemanticRole.DATA,
						0.91,
						List.of(new AiSemanticReason(
								"tabular_values",
								"헤더 아래 반복 데이터",
								List.of("Sales!A1:D3")))));
	}

	private AiWorkbookSummary.CellSnapshot cellSnapshot() {
		return new AiWorkbookSummary.CellSnapshot(
				"A1",
				"상품",
				null,
				null,
				"General",
				true,
				null,
				"center",
				false,
				new AiSemanticClassification(
						SemanticRole.HEADER,
						0.86,
						List.of(new AiSemanticReason(
								"header_style",
								"굵은 글꼴과 배경색",
								List.of("Sales!A1")))));
	}

	private AiWorkbookInsights workbookInsights() {
		return new AiWorkbookInsights(
				workbookSummary(),
				new AiWorkbookInsights.InsightReport(
						"수식 구조를 검토했습니다.",
						List.of(new AiWorkbookInsights.Insight(
								"수식 참조 확인",
								"Sales 시트의 수식 참조를 확인해야 합니다.",
								"formula",
								"warning",
								List.of("Sales!D2"),
								"참조 범위를 검토하세요.")),
						List.of("실제 셀 값은 분석하지 않았습니다.")));
	}
}
