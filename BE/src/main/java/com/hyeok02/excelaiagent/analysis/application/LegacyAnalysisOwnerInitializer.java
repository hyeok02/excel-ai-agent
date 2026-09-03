package com.hyeok02.excelaiagent.analysis.application;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisJobRepository;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class LegacyAnalysisOwnerInitializer implements ApplicationRunner {
	private final AnalysisJobRepository repository;
	private final AuthProperties authProperties;

	public LegacyAnalysisOwnerInitializer(
			AnalysisJobRepository repository,
			AuthProperties authProperties) {
		this.repository = repository;
		this.authProperties = authProperties;
	}

	@Override
	@Transactional
	public void run(ApplicationArguments args) {
		repository.assignUnownedTo(authProperties.bootstrap().username());
	}
}
