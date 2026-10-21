package com.hyeok02.excelaiagent.analysis.api;

import static java.util.concurrent.TimeUnit.SECONDS;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.function.BooleanSupplier;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.analysis.application.AnalysisJobProcessor;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.io.Resource;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@SpringBootTest(classes = BackendApplication.class, properties = {
		"app.analysis.async-enabled=true", "app.storage.upload-dir=build/test-deletion-race-uploads",
		"spring.datasource.url=jdbc:h2:mem:deletion-race;MODE=PostgreSQL;DB_CLOSE_DELAY=-1;DATABASE_TO_LOWER=TRUE"
})
class AnalysisDeletionRaceTests extends AnalysisControllerTestSupport {
	@Autowired private AnalysisJobProcessor processor;
	@Autowired @Qualifier("analysisTaskExecutor") private ThreadPoolTaskExecutor executor;
	private final CountDownLatch started = new CountDownLatch(1);
	private final CountDownLatch release = new CountDownLatch(1);

	@AfterEach
	void releaseAndJoinWorker() throws Exception {
		release.countDown();
		awaitWorkers();
	}

	@ParameterizedTest
	@ValueSource(booleans = {false, true})
	void deletedProcessingJobStaysDeletedAfterLateSuccessOrFailure(boolean fail) throws Exception {
		UUID id = submitPaused(fail);
		mockMvc.perform(delete("/api/v1/analyses/{id}", id)).andExpect(status().isNoContent());
		assertDeleted(id);
		release.countDown();
		awaitWorkers();
		assertDeleted(id);
		mockMvc.perform(get("/api/v1/analyses")).andExpect(status().isOk())
				.andExpect(jsonPath("$.content").isEmpty());
	}

	@Test
	void duplicateWorkersCannotFailActiveOrCompletedJobOrCallAiAgain() throws Exception {
		UUID id = submitPaused(false);
		long finishedBefore = executor.getThreadPoolExecutor().getCompletedTaskCount();
		processor.process(id, AnalysisDepth.AUTO);
		await(() -> executor.getThreadPoolExecutor().getCompletedTaskCount() > finishedBefore);
		assertThat(analysisJobRepository.findById(id).orElseThrow().getStatus())
				.isEqualTo(AnalysisStatus.PROCESSING);
		release.countDown();
		awaitWorkers();
		String originalResult = analysisResultRepository.findById(id).orElseThrow().getResultJson();
		long completedBeforeRepeat = executor.getThreadPoolExecutor().getCompletedTaskCount();
		processor.process(id, AnalysisDepth.AUTO);
		await(() -> executor.getThreadPoolExecutor().getCompletedTaskCount() > completedBeforeRepeat);
		awaitWorkers();
		verify(aiServiceClient, times(1)).summarizeWorkbook(any(Resource.class), anyBoolean());
		assertThat(analysisJobRepository.findById(id).orElseThrow().getStatus())
				.isEqualTo(AnalysisStatus.COMPLETED);
		assertThat(analysisResultRepository.findById(id).orElseThrow().getResultJson())
				.isEqualTo(originalResult);
	}

	@Test
	void deletionAfterCompletionRemovesResultAndSource() throws Exception {
		UUID id = submitPaused(false);
		release.countDown();
		awaitWorkers();
		assertThat(analysisResultRepository.findById(id)).isPresent();
		mockMvc.perform(delete("/api/v1/analyses/{id}", id)).andExpect(status().isNoContent());
		assertDeleted(id);
	}

	private UUID submitPaused(boolean fail) throws Exception {
		when(aiServiceClient.summarizeWorkbook(any(Resource.class), anyBoolean())).thenAnswer(call -> {
			started.countDown();
			if (!release.await(10, SECONDS)) throw new IllegalStateException("Test worker timed out");
			if (fail) throw new IllegalStateException("Simulated offline analysis failure");
			return AnalysisWorkbookFixture.summary();
		});
		String body = mockMvc.perform(multipart("/api/v1/analyses")
				.file(excel("workbook.xlsx")).param("mode", "BFS"))
				.andExpect(status().isAccepted()).andReturn().getResponse().getContentAsString();
		assertThat(started.await(5, SECONDS)).isTrue();
		return UUID.fromString(JsonPath.read(body, "$.analysisId"));
	}

	private void assertDeleted(UUID id) throws Exception {
		mockMvc.perform(get("/api/v1/analyses/{id}", id)).andExpect(status().isNotFound());
		mockMvc.perform(get("/api/v1/analyses/{id}/result", id)).andExpect(status().isNotFound());
		assertThat(analysisJobRepository.findById(id)).isEmpty();
		assertThat(analysisResultRepository.findById(id)).isEmpty();
		assertThat(analysisFileStorage.exists(id, "xlsx")).isFalse();
	}

	private void awaitWorkers() throws InterruptedException {
		await(() -> executor.getActiveCount() == 0 && executor.getQueueSize() == 0);
	}

	private void await(BooleanSupplier condition) throws InterruptedException {
		Instant deadline = Instant.now().plusSeconds(5);
		while (!condition.getAsBoolean() && Instant.now().isBefore(deadline)) Thread.sleep(20);
		assertThat(condition.getAsBoolean()).isTrue();
	}
}
