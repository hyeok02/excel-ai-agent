package com.hyeok02.excelaiagent.analysis.api;

import static java.util.concurrent.TimeUnit.SECONDS;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisResultRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWorkbookSummary;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.Resource;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;

@SpringBootTest(
		classes = BackendApplication.class,
		properties = {
				"app.analysis.async-enabled=true",
				"app.storage.upload-dir=build/test-async-uploads",
				"app.storage.cleanup-initial-delay=24h"
		})
@AutoConfigureMockMvc
class AsyncAnalysisControllerTests {

	private static final byte[] ZIP_FILE = {0x50, 0x4b, 0x03, 0x04, 0x01};

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private AnalysisJobRepository analysisJobRepository;

	@Autowired
	private AnalysisResultRepository analysisResultRepository;

	@MockitoBean
	private AiServiceClient aiServiceClient;

	private CountDownLatch releaseAnalysis;

	@BeforeEach
	void setUp() {
		analysisResultRepository.deleteAll();
		analysisJobRepository.deleteAll();
		reset(aiServiceClient);
		releaseAnalysis = new CountDownLatch(1);
	}

	@AfterEach
	void releaseWorker() {
		releaseAnalysis.countDown();
	}

	@Test
	void returnsQueuedBeforeAsynchronousAiAnalysisCompletes() throws Exception {
		CountDownLatch analysisStarted = new CountDownLatch(1);
		when(aiServiceClient.summarizeWorkbook(any(Resource.class))).thenAnswer(invocation -> {
			analysisStarted.countDown();
			if (!releaseAnalysis.await(5, SECONDS)) {
				throw new IllegalStateException("테스트 분석 대기 시간이 초과되었습니다.");
			}
			return new AiWorkbookSummary("async.xlsx", 0, List.of());
		});

		String responseBody = mockMvc.perform(multipart("/api/v1/analyses")
					.file(new MockMultipartFile("file", "async.xlsx", null, ZIP_FILE))
					.param("mode", "BFS"))
				.andExpect(status().isAccepted())
				.andExpect(jsonPath("$.status").value("QUEUED"))
				.andReturn()
				.getResponse()
				.getContentAsString();

		assertThat(analysisStarted.await(2, SECONDS)).isTrue();
		UUID analysisId = UUID.fromString(JsonPath.read(responseBody, "$.analysisId"));
		assertThat(analysisJobRepository.findById(analysisId).orElseThrow().getStatus())
				.isEqualTo(AnalysisStatus.PROCESSING);

		releaseAnalysis.countDown();
		awaitStatus(analysisId, AnalysisStatus.COMPLETED, Duration.ofSeconds(5));
		assertThat(analysisResultRepository.findById(analysisId)).isPresent();
	}

	private void awaitStatus(UUID analysisId, AnalysisStatus expected, Duration timeout)
			throws InterruptedException {
		Instant deadline = Instant.now().plus(timeout);
		while (Instant.now().isBefore(deadline)) {
			if (analysisJobRepository.findById(analysisId)
					.map(job -> job.getStatus() == expected)
					.orElse(false)) {
				return;
			}
			Thread.sleep(50);
		}
		assertThat(analysisJobRepository.findById(analysisId).orElseThrow().getStatus())
				.isEqualTo(expected);
	}
}
