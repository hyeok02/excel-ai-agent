package com.hyeok02.excelaiagent.auth.application;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.domain.AppUserRepository;
import com.hyeok02.excelaiagent.auth.domain.UserRole;
import com.hyeok02.excelaiagent.auth.error.LastActiveAdminException;
import com.hyeok02.excelaiagent.auth.error.SelfDeactivationException;
import com.hyeok02.excelaiagent.auth.error.SsoAccessDeniedException;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;

class UserAccountServiceTests {

	private static final Instant NOW = Instant.parse("2026-09-30T04:00:00Z");

	private final AppUserRepository repository = mock(AppUserRepository.class);
	private final UserAccountService service = new UserAccountService(
			repository,
			mock(PasswordEncoder.class),
			new AuthProperties(
					true,
					"http://localhost:5173",
					new AuthProperties.Bootstrap("admin", "admin1234", "Admin"),
					new AuthProperties.Sso(true, "company", "example.com", true)),
			Clock.fixed(NOW, ZoneOffset.UTC));

	@Test
	void refusesToDeactivateCurrentAccount() {
		AppUser admin = user("admin", UserRole.ADMIN);
		assertThrows(SelfDeactivationException.class, () ->
				service.updateUserStatus(admin.getUserId(), false, admin.getUserId()));
		assertTrue(admin.isEnabled());
	}

	@Test
	void refusesToDeactivateLastActiveAdmin() {
		AppUser admin = user("only-admin", UserRole.ADMIN);
		when(repository.findRoleByUserId(admin.getUserId()))
				.thenReturn(Optional.of(UserRole.ADMIN));
		when(repository.findAllByRoleForUpdate(UserRole.ADMIN)).thenReturn(List.of(admin));

		assertThrows(LastActiveAdminException.class, () ->
				service.updateUserStatus(admin.getUserId(), false, user("actor", UserRole.USER).getUserId()));
		assertTrue(admin.isEnabled());
	}

	@Test
	void deactivatesAdminWhenAnotherActiveAdminRemains() {
		AppUser target = user("target-admin", UserRole.ADMIN);
		AppUser actor = user("actor-admin", UserRole.ADMIN);
		when(repository.findRoleByUserId(target.getUserId()))
				.thenReturn(Optional.of(UserRole.ADMIN));
		when(repository.findAllByRoleForUpdate(UserRole.ADMIN))
				.thenReturn(List.of(actor, target));

		AppUser updated = service.updateUserStatus(
				target.getUserId(), false, actor.getUserId());

		assertFalse(updated.isEnabled());
	}

	@Test
	void refusesSsoLoginForDisabledExistingAccount() {
		AppUser ssoUser = AppUser.sso("disabled", "Disabled", "disabled@example.com", NOW);
		ssoUser.updateEnabled(false, NOW.plusSeconds(1));
		when(repository.findByEmailIgnoreCase("disabled@example.com"))
				.thenReturn(Optional.of(ssoUser));

		assertThrows(SsoAccessDeniedException.class, () ->
				service.findOrProvisionSsoUser("DISABLED@example.com", "Updated"));
		assertEquals("Disabled", ssoUser.getDisplayName());
	}

	@Test
	void resolvesDisabledOidcSessionByEmail() {
		AppUser ssoUser = AppUser.sso("disabled", "Disabled", "disabled@example.com", NOW);
		ssoUser.updateEnabled(false, NOW.plusSeconds(1));
		OidcUser oidcUser = mock(OidcUser.class);
		Authentication authentication = mock(Authentication.class);
		when(authentication.isAuthenticated()).thenReturn(true);
		when(authentication.getPrincipal()).thenReturn(oidcUser);
		when(oidcUser.getEmail()).thenReturn("disabled@example.com");
		when(repository.findByEmailIgnoreCase("disabled@example.com"))
				.thenReturn(Optional.of(ssoUser));

		assertFalse(service.isAuthenticationEnabled(authentication));
	}

	private static AppUser user(String username, UserRole role) {
		return AppUser.local(username, "hash", username, role, NOW);
	}

}
