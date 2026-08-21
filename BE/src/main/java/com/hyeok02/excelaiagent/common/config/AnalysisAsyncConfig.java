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

	@Bean(name = "analysisTaskExecutor")
	public Executor analysisTaskExecutor(
			@Value("${app.analysis.async-enabled:true}") boolean asyncEnabled) {
		if (!asyncEnabled) {
			return new SyncTaskExecutor();
		}

		ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
		executor.setCorePoolSize(2);
		executor.setMaxPoolSize(4);
		executor.setQueueCapacity(100);
		executor.setThreadNamePrefix("analysis-");
		return executor;
	}
}
