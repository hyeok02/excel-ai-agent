package com.hyeok02.excelaiagent.auth.application;

import java.time.Clock;
import java.time.Instant;
import java.util.Locale;

import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.error.SsoAccessDeniedException;
import com.hyeok02.excelaiagent.common.config.AuthProperties;

/**
 * SSO로 들어온 사용자를 찾거나 새로 등록한다.
 *
 * 허용 도메인 검사와 아이디 중복 회피 규칙이 사내 계정 발급과 달라 따로 둔다.
 */
final class SsoUserAccounts {
	private final AppUserRepository appUserRepository;
	private final AuthProperties authProperties;
	private final Clock clock;

	SsoUserAccounts(
			AppUserRepository appUserRepository, AuthProperties authProperties, Clock clock) {
		this.appUserRepository = appUserRepository;
		this.authProperties = authProperties;
		this.clock = clock;
	}

	AppUser findOrProvision(String email, String displayName) {
		String normalizedEmail = email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
		validateSsoDomain(normalizedEmail);
		return appUserRepository.findByEmailIgnoreCase(normalizedEmail)
				.map(user -> {
					if (!user.isEnabled()) {
						throw new SsoAccessDeniedException("비활성화된 계정입니다. 관리자에게 문의해주세요.");
					}
					String safeDisplayName = displayName == null || displayName.isBlank()
							? user.getDisplayName()
							: displayName.trim();
					user.updateSsoProfile(safeDisplayName, Instant.now(clock));
					return user;
				})
				.orElseGet(() -> provisionSsoUser(normalizedEmail, displayName));
	}

	private AppUser provisionSsoUser(String email, String displayName) {
		if (!authProperties.sso().autoProvision()) {
			throw new SsoAccessDeniedException("관리자에게 SSO 계정 등록을 요청해주세요.");
		}
		String baseUsername = email.substring(0, email.indexOf('@'));
		String username = uniqueUsername(baseUsername);
		return appUserRepository.save(AppUser.sso(
				username,
				displayName == null || displayName.isBlank() ? username : displayName.trim(),
				email,
				Instant.now(clock)));
	}

	private void validateSsoDomain(String email) {
		if (!email.contains("@")) {
			throw new SsoAccessDeniedException("SSO 공급자가 이메일 정보를 제공하지 않았습니다.");
		}
		String allowedDomain = authProperties.sso().allowedDomain();
		if (!allowedDomain.isBlank() && !email.endsWith("@" + allowedDomain)) {
			throw new SsoAccessDeniedException("허용된 회사 이메일 계정이 아닙니다.");
		}
	}

	private String uniqueUsername(String baseUsername) {
		String candidate = normalizeUsername(baseUsername);
		int suffix = 1;
		while (appUserRepository.existsByUsernameIgnoreCase(candidate)) {
			candidate = normalizeUsername(baseUsername) + suffix++;
		}
		return candidate;
	}

	static String normalizeUsername(String username) {
		return username.trim().toLowerCase(Locale.ROOT);
	}
}
