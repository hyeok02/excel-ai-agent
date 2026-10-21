package com.hyeok02.excelaiagent.analysis.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import com.hyeok02.excelaiagent.analysis.application.AnalysisJobLifecycle;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisJob;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

class AnalysisJobLifecycleTests extends AnalysisControllerTestSupport {
	@Autowired private AnalysisJobLifecycle lifecycle;
	@Autowired private PlatformTransactionManager transactions;

	@Test
	void simultaneousClaimsOnlyAllowOneWorker() throws Exception {
		UUID id = queued();
		CountDownLatch start = new CountDownLatch(1);
		try (var workers = Executors.newFixedThreadPool(2)) {
			var first = workers.submit(() -> { start.await(); return lifecycle.claim(id).isPresent(); });
			var second = workers.submit(() -> { start.await(); return lifecycle.claim(id).isPresent(); });
			start.countDown();
			assertThat(first.get(5, TimeUnit.SECONDS) ^ second.get(5, TimeUnit.SECONDS)).isTrue();
		}
		assertStatus(id, AnalysisStatus.PROCESSING);
	}

	@Test
	void completedResultIsNotReplacedOrMarkedFailedByDuplicateCallbacks() {
		UUID id = queued();
		assertThat(lifecycle.claim(id)).isPresent();
		assertThat(lifecycle.complete(id, "{\"original\":true}")).isTrue();
		assertThat(lifecycle.complete(id, "{\"replacement\":true}")).isFalse();
		assertThat(lifecycle.fail(id, "Late failure")).isFalse();
		assertThat(lifecycle.claim(id)).isEmpty();
		assertStatus(id, AnalysisStatus.COMPLETED);
		assertThat(analysisResultRepository.findById(id).orElseThrow().getResultJson())
				.isEqualTo("{\"original\":true}");
	}

	@Test
	void failedOrUnclaimedJobsCannotReceiveResults() {
		UUID id = queued();
		assertThat(lifecycle.complete(id, "{}")).isFalse();
		assertThat(lifecycle.fail(id, "Premature failure")).isFalse();
		assertThat(lifecycle.claim(id)).isPresent();
		assertThat(lifecycle.fail(id, "First failure")).isTrue();
		assertThat(lifecycle.fail(id, "Second failure")).isFalse();
		assertThat(lifecycle.complete(id, "{}")).isFalse();
		assertThat(lifecycle.claim(id)).isEmpty();
		assertStatus(id, AnalysisStatus.FAILED);
		assertThat(analysisJobRepository.findById(id).orElseThrow().getFailureMessage())
				.isEqualTo("First failure");
		assertThat(analysisResultRepository.findById(id)).isEmpty();
	}

	@Test
	void missingJobsAreNeverInsertedByCallbacks() {
		UUID id = UUID.randomUUID();
		assertThat(lifecycle.claim(id)).isEmpty();
		assertThat(lifecycle.complete(id, "{}")).isFalse();
		assertThat(lifecycle.fail(id, "Late failure")).isFalse();
		assertThat(analysisJobRepository.findById(id)).isEmpty();
		assertThat(analysisResultRepository.findById(id)).isEmpty();
	}

	@Test
	void resultAndCompletionRollBackTogether() {
		UUID id = queued();
		lifecycle.claim(id);
		assertThatThrownBy(() -> new TransactionTemplate(transactions).executeWithoutResult(status -> {
			assertThat(lifecycle.complete(id, "{}")).isTrue();
			assertThat(analysisResultRepository.findById(id)).isPresent();
			assertStatus(id, AnalysisStatus.COMPLETED);
			throw new IllegalStateException("Simulated commit failure");
		})).isInstanceOf(IllegalStateException.class);
		assertStatus(id, AnalysisStatus.PROCESSING);
		assertThat(analysisResultRepository.findById(id)).isEmpty();
	}

	@Test
	void failedResultPersistenceDoesNotCompleteJobOrLeaveResult() {
		UUID id = queued();
		lifecycle.claim(id);
		assertThatThrownBy(() -> lifecycle.complete(id, null)).isInstanceOf(RuntimeException.class);
		assertStatus(id, AnalysisStatus.PROCESSING);
		assertThat(analysisResultRepository.findById(id)).isEmpty();
		assertThat(lifecycle.fail(id, null)).isTrue();
		assertStatus(id, AnalysisStatus.FAILED);
	}

	private UUID queued() {
		return analysisJobRepository.saveAndFlush(AnalysisJob.queued(
				UUID.randomUUID(), AnalysisMode.BFS, "workbook.xlsx", "xlsx", 5,
				"system", false, Instant.now())).getAnalysisId();
	}

	private void assertStatus(UUID id, AnalysisStatus expected) {
		assertThat(analysisJobRepository.findById(id).orElseThrow().getStatus()).isEqualTo(expected);
	}
}
