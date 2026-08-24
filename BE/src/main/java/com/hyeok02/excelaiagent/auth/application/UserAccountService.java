package com.hyeok02.excelaiagent.auth.application;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Locale;

import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.AuthProvider;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.auth.error.DuplicateUsernameException;
import com.hyeok02.excelaiagent.auth.error.SsoAccessDeniedException;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import jakarta.transaction.Transactional;

import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserAccountService implements UserDetailsService {

	private final AppUserRepository appUserRepository;
	private final PasswordEncoder passwordEncoder;
	private final AuthProperties authProperties;
	private final Clock clock;

	@Autowired
	public UserAccountService(
			AppUserRepository appUserRepository,
			PasswordEncoder passwordEncoder,
			AuthProperties authProperties) {
		this(appUserRepository, passwordEncoder, authProperties, Clock.systemUTC());
	}

	UserAccountService(
			AppUserRepository appUserRepository,
			PasswordEncoder passwordEncoder,
			AuthProperties authProperties,
			Clock clock) {
		this.appUserRepository = appUserRepository;
		this.passwordEncoder = passwordEncoder;
		this.authProperties = authProperties;
		this.clock = clock;
	}

	@Transactional
	public AppUser createLocalUser(
			String username,
			String rawPassword,
			String displayName,
			UserRole role) {
		String normalizedUsername = normalizeUsername(username);
		if (appUserRepository.existsByUsernameIgnoreCase(normalizedUsername)) {
			throw new DuplicateUsernameException(normalizedUsername);
		}
		AppUser user = AppUser.local(
				normalizedUsername,
				passwordEncoder.encode(rawPassword),
				displayName.trim(),
				role,
				Instant.now(clock));
		return appUserRepository.save(user);
	}

	@Transactional
	public AppUser findOrProvisionSsoUser(String email, String displayName) {
		String normalizedEmail = email == null ? "" : email.trim().toLowerCase(Locale.ROOT);
		validateSsoDomain(normalizedEmail);
		return appUserRepository.findByEmailIgnoreCase(normalizedEmail)
				.map(user -> {
					String safeDisplayName = displayName == null || displayName.isBlank()
							? user.getDisplayName()
							: displayName.trim();
					user.updateSsoProfile(safeDisplayName, Instant.now(clock));
					return user;
				})
				.orElseGet(() -> provisionSsoUser(normalizedEmail, displayName));
	}

	public AppUser requireByUsername(String username) {
		return appUserRepository.findByUsernameIgnoreCase(username)
				.orElseThrow(() -> new UsernameNotFoundException("사용자를 찾을 수 없습니다."));
	}

	public AppUser requireByEmail(String email) {
		return appUserRepository.findByEmailIgnoreCase(email)
				.orElseThrow(() -> new UsernameNotFoundException("SSO 사용자를 찾을 수 없습니다."));
	}

	public List<AppUser> listUsers() {
		return appUserRepository.findAllByOrderByCreatedAtDesc();
	}

	@Override
	public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
		AppUser user = requireByUsername(username);
		if (user.getAuthProvider() != AuthProvider.LOCAL || user.getPasswordHash() == null) {
			throw new UsernameNotFoundException("사내 계정 로그인 대상이 아닙니다.");
		}
		return User.withUsername(user.getUsername())
				.password(user.getPasswordHash())
				.roles(user.getRole().name())
				.disabled(!user.isEnabled())
				.build();
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

	private static String normalizeUsername(String username) {
		return username.trim().toLowerCase(Locale.ROOT);
	}
}
