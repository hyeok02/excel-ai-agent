package com.hyeok02.excelaiagent.common.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.concurrent.Executor;

import org.junit.jupiter.api.Test;
import org.springframework.core.task.SyncTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

class AnalysisAsyncConfigTests {
	private final AnalysisAsyncConfig config = new AnalysisAsyncConfig();

	@Test
	void runsAsManyAnalysesAtOnceAsItWasAskedTo() {
		// core만 차면 나머지를 줄 세우는 스레드풀 특성 탓에, core가 max보다 작으면
		// 설정한 수만큼 동시에 돌지 않는다. 둘을 같게 두어야 설정대로 돈다.
		ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) config
				.analysisTaskExecutor(true, 4, 8);

		assertThat(executor.getCorePoolSize()).isEqualTo(4);
		assertThat(executor.getMaxPoolSize()).isEqualTo(4);
	}

	@Test
	void keepsTheWaitingQueueShortEnoughToBeWorthWaitingFor() {
		ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) config
				.analysisTaskExecutor(true, 4, 8);
		executor.initialize();

		assertThat(executor.getThreadPoolExecutor().getQueue().remainingCapacity())
				.isEqualTo(8);
	}

	@Test
	void runsInlineWhenAsynchronousAnalysisIsTurnedOff() {
		Executor executor = config.analysisTaskExecutor(false, 4, 8);

		assertThat(executor).isInstanceOf(SyncTaskExecutor.class);
	}
}
