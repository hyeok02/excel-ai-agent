package com.hyeok02.excelaiagent.auth.application;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.common.config.AuthProperties;

import org.junit.jupiter.api.Test;

class BootstrapAdminInitializerTests {

	private final AppUserRepository appUserRepository = mock(AppUserRepository.class);

	private final UserAccountService userAccountService = mock(UserAccountService.class);

	@Test
	void refusesToStartWithoutAnAdminPassword() {
		assertThatThrownBy(() -> initializer(true, "").run(null))
				.isInstanceOf(IllegalStateException.class)
				.hasMessageContaining("BOOTSTRAP_ADMIN_PASSWORD");

		verify(userAccountService, never())
				.createLocalUser(any(), any(), any(), any());
	}

	@Test
	void refusesToStartWithAShortAdminPassword() {
		assertThatThrownBy(() -> initializer(true, "admin1234").run(null))
				.isInstanceOf(IllegalStateException.class)
				.hasMessageContaining("12자 이상");

		verify(userAccountService, never())
				.createLocalUser(any(), any(), any(), any());
	}

	@Test
	void createsTheAdminWithTheConfiguredPassword() {
		when(appUserRepository.existsByUsernameIgnoreCase("admin")).thenReturn(false);

		initializer(true, "a-long-enough-password").run(null);

		verify(userAccountService).createLocalUser(
				eq("admin"), eq("a-long-enough-password"), any(), eq(UserRole.ADMIN));
	}

	@Test
	void skipsThePasswordCheckWhenSecurityIsOff() {
		when(appUserRepository.existsByUsernameIgnoreCase("admin")).thenReturn(true);

		initializer(false, "").run(null);

		verify(userAccountService, never())
				.createLocalUser(any(), any(), any(), any());
	}

	private BootstrapAdminInitializer initializer(boolean securityEnabled, String password) {
		AuthProperties properties = new AuthProperties(
				securityEnabled,
				"http://localhost:5173",
				new AuthProperties.Bootstrap("admin", password, "System Administrator"),
				null);
		return new BootstrapAdminInitializer(
				appUserRepository, userAccountService, properties);
	}
}
