package com.hyeok02.excelaiagent.auth.application;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.AuthProvider;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.auth.error.DuplicateUsernameException;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import jakarta.transaction.Transactional;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

@Service
public class UserAccountService implements UserDetailsService {

	private final AppUserRepository appUserRepository;
	private final PasswordEncoder passwordEncoder;
	private final Clock clock;
	private final SsoUserAccounts ssoAccounts;
	private final UserStatusChanges statusChanges;

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
		this.clock = clock;
		this.ssoAccounts = new SsoUserAccounts(appUserRepository, authProperties, clock);
		this.statusChanges = new UserStatusChanges(appUserRepository, clock);
	}

	@Transactional
	public AppUser findOrProvisionSsoUser(String email, String displayName) {
		return ssoAccounts.findOrProvision(email, displayName);
	}

	@Transactional
	public AppUser updateUserStatus(UUID userId, boolean enabled, UUID actorUserId) {
		return statusChanges.apply(userId, enabled, actorUserId);
	}

	@Transactional
	public AppUser createLocalUser(
			String username,
			String rawPassword,
			String displayName,
			UserRole role) {
		String normalizedUsername = SsoUserAccounts.normalizeUsername(username);
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

	public AppUser requireAuthenticatedUser(Authentication authentication) {
		if (authentication == null || !authentication.isAuthenticated()) {
			throw new UsernameNotFoundException("인증된 사용자를 찾을 수 없습니다.");
		}
		return authentication.getPrincipal() instanceof OidcUser oidcUser
				? requireByEmail(oidcUser.getEmail())
				: requireByUsername(authentication.getName());
	}

	public boolean isAuthenticationEnabled(Authentication authentication) {
		try {
			return requireAuthenticatedUser(authentication).isEnabled();
		}
		catch (UsernameNotFoundException exception) {
			return false;
		}
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
}
