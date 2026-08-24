package com.hyeok02.excelaiagent.auth.api;

import com.hyeok02.excelaiagent.auth.application.UserAccountService;
import com.hyeok02.excelaiagent.auth.domain.AppUser;
import com.hyeok02.excelaiagent.auth.error.InvalidCredentialsException;
import com.hyeok02.excelaiagent.common.config.AuthProperties;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

	private final AuthenticationManager authenticationManager;
	private final SecurityContextRepository securityContextRepository;
	private final UserAccountService userAccountService;
	private final AuthProperties authProperties;

	public AuthController(
			AuthenticationManager authenticationManager,
			SecurityContextRepository securityContextRepository,
			UserAccountService userAccountService,
			AuthProperties authProperties) {
		this.authenticationManager = authenticationManager;
		this.securityContextRepository = securityContextRepository;
		this.userAccountService = userAccountService;
		this.authProperties = authProperties;
	}

	@PostMapping("/login")
	public CurrentUserResponse login(
			@Valid @RequestBody LoginRequest loginRequest,
			HttpServletRequest request,
			HttpServletResponse response) {
		try {
			Authentication authentication = authenticationManager.authenticate(
					UsernamePasswordAuthenticationToken.unauthenticated(
							loginRequest.username().trim(), loginRequest.password()));
			SecurityContext context = SecurityContextHolder.createEmptyContext();
			context.setAuthentication(authentication);
			SecurityContextHolder.setContext(context);
			securityContextRepository.saveContext(context, request, response);
			return CurrentUserResponse.from(userAccountService.requireByUsername(authentication.getName()));
		}
		catch (AuthenticationException exception) {
			throw new InvalidCredentialsException();
		}
	}

	@GetMapping("/me")
	public ResponseEntity<CurrentUserResponse> currentUser(Authentication authentication) {
		if (authentication == null || !authentication.isAuthenticated()
				|| "anonymousUser".equals(authentication.getPrincipal())) {
			return ResponseEntity.status(401).build();
		}
		AppUser user = authentication.getPrincipal() instanceof OidcUser oidcUser
				? userAccountService.requireByEmail(oidcUser.getEmail())
				: userAccountService.requireByUsername(authentication.getName());
		return ResponseEntity.ok(CurrentUserResponse.from(user));
	}

	@GetMapping("/config")
	public AuthConfigResponse config() {
		return new AuthConfigResponse(
				authProperties.sso().enabled(),
				"/oauth2/authorization/" + authProperties.sso().registrationId());
	}

	@GetMapping("/csrf")
	public CsrfResponse csrf(CsrfToken csrfToken) {
		return new CsrfResponse(csrfToken.getHeaderName(), csrfToken.getParameterName(), csrfToken.getToken());
	}

	@PostMapping("/logout")
	public ResponseEntity<Void> logout(
			Authentication authentication,
			HttpServletRequest request,
			HttpServletResponse response) {
		new SecurityContextLogoutHandler().logout(request, response, authentication);
		return ResponseEntity.noContent().build();
	}

	public record LoginRequest(
			@NotBlank(message = "아이디를 입력해주세요.") String username,
			@NotBlank(message = "비밀번호를 입력해주세요.") String password) {
	}

	public record CurrentUserResponse(
			String id,
			String username,
			String displayName,
			String email,
			String role,
			String authProvider) {

		private static CurrentUserResponse from(AppUser user) {
			return new CurrentUserResponse(
					user.getUserId().toString(),
					user.getUsername(),
					user.getDisplayName(),
					user.getEmail(),
					user.getRole().name(),
					user.getAuthProvider().name());
		}
	}

	public record AuthConfigResponse(boolean ssoEnabled, String ssoLoginPath) {
	}

	public record CsrfResponse(String headerName, String parameterName, String token) {
	}
}
