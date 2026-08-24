package com.hyeok02.excelaiagent.auth.application;

import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.common.config.AuthProperties;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class BootstrapAdminInitializer implements ApplicationRunner {

	private final AppUserRepository appUserRepository;
	private final UserAccountService userAccountService;
	private final AuthProperties authProperties;

	public BootstrapAdminInitializer(
			AppUserRepository appUserRepository,
			UserAccountService userAccountService,
			AuthProperties authProperties) {
		this.appUserRepository = appUserRepository;
		this.userAccountService = userAccountService;
		this.authProperties = authProperties;
	}

	@Override
	public void run(ApplicationArguments args) {
		AuthProperties.Bootstrap admin = authProperties.bootstrap();
		if (!appUserRepository.existsByUsernameIgnoreCase(admin.username())) {
			userAccountService.createLocalUser(
					admin.username(), admin.password(), admin.displayName(), UserRole.ADMIN);
		}
	}
}
