package com.hyeok02.excelaiagent.analysis.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class InterruptedAnalysisRecoveryRunnerTests {

	@Autowired
	private InterruptedAnalysisRecoveryRunner runner;

	@Autowired
	private AnalysisJobRepository analysisJobRepository;

	@BeforeEach
	void prepare() {
		analysisJobRepository.deleteAll();
	}

	@Test
	void failsJobsLeftQueuedByAServerRestart() {
		UUID analysisId = save(AnalysisStatus.QUEUED).getAnalysisId();

		runner.run(null);

		AnalysisJob recovered = analysisJobRepository.findById(analysisId).orElseThrow();
		assertThat(recovered.getStatus()).isEqualTo(AnalysisStatus.FAILED);
		assertThat(recovered.getFailureMessage()).contains("서버가 재시작되어");
	}

	@Test
	void failsJobsLeftProcessingByAServerRestart() {
		UUID analysisId = save(AnalysisStatus.PROCESSING).getAnalysisId();

		runner.run(null);

		assertThat(analysisJobRepository.findById(analysisId).orElseThrow().getStatus())
				.isEqualTo(AnalysisStatus.FAILED);
	}

	@Test
	void leavesFinishedJobsUntouched() {
		UUID completedId = save(AnalysisStatus.COMPLETED).getAnalysisId();
		UUID failedId = save(AnalysisStatus.FAILED).getAnalysisId();

		runner.run(null);

		assertThat(analysisJobRepository.findById(completedId).orElseThrow().getStatus())
				.isEqualTo(AnalysisStatus.COMPLETED);
		assertThat(analysisJobRepository.findById(failedId).orElseThrow().getFailureMessage())
				.isNull();
	}

	private AnalysisJob save(AnalysisStatus status) {
		Instant now = Instant.now();
		AnalysisJob job = AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "sales.xlsx", "xlsx", 100L, "system", now);
		if (status != AnalysisStatus.QUEUED) {
			job.markProcessing(now);
		}
		if (status == AnalysisStatus.COMPLETED) {
			job.markCompleted(now);
		}
		if (status == AnalysisStatus.FAILED) {
			job.markFailed(now);
		}
		return analysisJobRepository.save(job);
	}
}
