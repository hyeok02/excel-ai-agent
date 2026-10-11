package com.hyeok02.excelaiagent.common.config;

import java.util.concurrent.Executor;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.SyncTaskExecutor;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@Configuration
@EnableAsync
@EnableScheduling
public class AnalysisAsyncConfig {

	/**
	 * 대기열은 화면이 기다려 주는 시간 안에 처리될 만큼만 둔다.
	 *
	 * 자바 스레드풀은 대기열이 가득 차야 core를 넘겨 스레드를 늘린다. core 2에
	 * 대기열 100이던 설정은 실제로는 늘 2건만 동시에 돌면서 최대 100건을 줄 세워,
	 * 화면이 포기하는 180초를 한참 넘긴 뒤에야 차례가 오는 작업을 만들었다.
	 * core와 max를 같게 두어 설정한 수만큼 실제로 동시에 돌게 하고, 대기열은
	 * 짧게 잡아 감당할 수 없는 요청은 줄 세우는 대신 바로 되돌려 보낸다.
	 */
	@Bean(name = "analysisTaskExecutor")
	public Executor analysisTaskExecutor(
			@Value("${app.analysis.async-enabled:true}") boolean asyncEnabled,
			@Value("${app.analysis.workers:4}") int workers,
			@Value("${app.analysis.queue-capacity:8}") int queueCapacity) {
		if (!asyncEnabled) {
			return new SyncTaskExecutor();
		}

		ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
		executor.setCorePoolSize(workers);
		executor.setMaxPoolSize(workers);
		executor.setQueueCapacity(queueCapacity);
		executor.setThreadNamePrefix("analysis-");
		return executor;
	}
}
