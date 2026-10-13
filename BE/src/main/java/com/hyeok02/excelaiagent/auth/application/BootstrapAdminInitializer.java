package com.hyeok02.excelaiagent.auth.application;

import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.common.config.AuthProperties;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class BootstrapAdminInitializer implements ApplicationRunner {

	static final int MIN_PASSWORD_LENGTH = 12;

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

	/**
	 * 최초 관리자 계정을 만든다. 비밀번호가 없거나 짧으면 아예 뜨지 않는다.
	 *
	 * 예전에는 비밀번호 기본값이 코드와 문서에 'admin1234'로 적혀 있었다. 설정을
	 * 잊으면 누구나 아는 비밀번호로 관리자 계정이 열린 채 서비스가 떠 버린다.
	 * 조용히 약한 계정을 만들고 경고만 남기는 것보다, 뜨지 않고 무엇을 설정해야
	 * 하는지 알려 주는 쪽이 안전하다.
	 */
	@Override
	public void run(ApplicationArguments args) {
		AuthProperties.Bootstrap admin = authProperties.bootstrap();
		if (authProperties.securityEnabled()) {
			requireUsablePassword(admin.password());
		}
		if (!appUserRepository.existsByUsernameIgnoreCase(admin.username())) {
			userAccountService.createLocalUser(
					admin.username(), admin.password(), admin.displayName(), UserRole.ADMIN);
		}
	}

	private static void requireUsablePassword(String password) {
		if (password == null || password.isBlank()) {
			throw new IllegalStateException(
					"최초 관리자 비밀번호가 설정되지 않았습니다. "
							+ "BOOTSTRAP_ADMIN_PASSWORD 환경변수에 "
							+ MIN_PASSWORD_LENGTH + "자 이상의 값을 넣고 다시 시작해주세요.");
		}
		if (password.length() < MIN_PASSWORD_LENGTH) {
			throw new IllegalStateException(
					"최초 관리자 비밀번호가 너무 짧습니다. "
							+ "BOOTSTRAP_ADMIN_PASSWORD 는 " + MIN_PASSWORD_LENGTH
							+ "자 이상이어야 합니다.");
		}
	}
}
