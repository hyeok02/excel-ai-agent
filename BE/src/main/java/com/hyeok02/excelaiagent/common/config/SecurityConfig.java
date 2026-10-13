package com.hyeok02.excelaiagent.common.config;

import java.io.IOException;
import java.util.List;

import com.hyeok02.excelaiagent.auth.application.CompanyOidcUserService;
import com.hyeok02.excelaiagent.auth.application.EnabledAccountFilter;
import com.hyeok02.excelaiagent.auth.application.UserAccountService;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextHolderFilter;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.authentication.session.ChangeSessionIdAuthenticationStrategy;
import org.springframework.security.web.authentication.session.CompositeSessionAuthenticationStrategy;
import org.springframework.security.web.authentication.session.SessionAuthenticationStrategy;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfAuthenticationStrategy;
import org.springframework.security.web.csrf.CsrfTokenRepository;

@Configuration
public class SecurityConfig {

	@Bean
	PasswordEncoder passwordEncoder() {
		return new BCryptPasswordEncoder();
	}

	@Bean
	SecurityContextRepository securityContextRepository() {
		return new HttpSessionSecurityContextRepository();
	}

	@Bean
	CsrfTokenRepository csrfTokenRepository() {
		CookieCsrfTokenRepository repository = CookieCsrfTokenRepository.withHttpOnlyFalse();
		repository.setHeaderName("X-XSRF-TOKEN");
		repository.setCookieCustomizer(cookie -> cookie.path("/").sameSite("Lax"));
		return repository;
	}

	/**
	 * 로그인에 성공하면 세션 ID와 CSRF 토큰을 모두 새로 발급한다.
	 *
	 * 로그인을 직접 구현한 엔드포인트는 스프링의 인증 필터를 거치지 않아 이 처리가
	 * 빠져 있었다. 그러면 공격자가 미리 받아 둔 세션 ID가 피해자의 로그인 이후에도
	 * 그대로 유효해, 그 ID만 들고 있으면 피해자 계정으로 들어올 수 있다.
	 *
	 * CSRF 토큰은 여기서 지워지고 다음 요청에서 다시 발급된다. 그래서 프런트엔드는
	 * 로그인 직후 /api/v1/auth/csrf 로 새 토큰을 한 번 받아 둔다.
	 */
	@Bean
	SessionAuthenticationStrategy sessionAuthenticationStrategy(
			CsrfTokenRepository csrfTokenRepository) {
		return new CompositeSessionAuthenticationStrategy(List.<SessionAuthenticationStrategy>of(
				new ChangeSessionIdAuthenticationStrategy(),
				new CsrfAuthenticationStrategy(csrfTokenRepository)));
	}

	@Bean
	AuthenticationManager authenticationManager(
			UserAccountService userAccountService,
			PasswordEncoder passwordEncoder) {
		DaoAuthenticationProvider provider = new DaoAuthenticationProvider(userAccountService);
		provider.setPasswordEncoder(passwordEncoder);
		return new ProviderManager(provider);
	}

	@Bean
	SecurityFilterChain securityFilterChain(
			HttpSecurity http,
			AuthProperties authProperties,
			CompanyOidcUserService companyOidcUserService,
			UserAccountService userAccountService,
			CsrfTokenRepository csrfTokenRepository) throws Exception {
		http
				.cors(Customizer.withDefaults())
				.exceptionHandling(exceptions -> exceptions
						.authenticationEntryPoint((request, response, exception) ->
								writeUnauthorized(response)))
				.logout(logout -> logout.disable());

		if (authProperties.securityEnabled()) {
			http.addFilterAfter(
					new EnabledAccountFilter(userAccountService),
					SecurityContextHolderFilter.class)
					.csrf(csrf -> csrf
					.csrfTokenRepository(csrfTokenRepository)
					.csrfTokenRequestHandler(new SpaCsrfTokenRequestHandler())
					.ignoringRequestMatchers("/api/v1/telegram/webhook"))
					.authorizeHttpRequests(authorize -> authorize
					.requestMatchers(
							"/health", "/actuator/health/**", "/v3/api-docs/**",
							"/swagger-ui/**", "/swagger-ui.html", "/oauth2/**", "/login/oauth2/**")
						.permitAll()
					.requestMatchers(HttpMethod.GET,
							"/api/v1/auth/me", "/api/v1/auth/config", "/api/v1/auth/csrf",
							"/api/v1/public/analysis-shares/*")
						.permitAll()
					.requestMatchers(HttpMethod.POST, "/api/v1/auth/login").permitAll()
					.requestMatchers(HttpMethod.POST, "/api/v1/telegram/webhook").permitAll()
					.requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
					.anyRequest().authenticated());
		}
		else {
			http.csrf(csrf -> csrf.disable())
					.authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll());
		}

		if (authProperties.sso().enabled()) {
			http.oauth2Login(oauth -> oauth
					.userInfoEndpoint(userInfo -> userInfo.oidcUserService(companyOidcUserService))
					.successHandler((request, response, authentication) -> response.sendRedirect(
							authProperties.frontendBaseUrl() + "/auth/callback"))
					.failureHandler((request, response, exception) -> response.sendRedirect(
							authProperties.frontendBaseUrl() + "/auth/callback?error=sso")));
		}

		return http.build();
	}

	private static void writeUnauthorized(HttpServletResponse response) throws IOException {
		response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.setCharacterEncoding("UTF-8");
		response.getWriter().write(
				"{\"status\":401,\"code\":\"UNAUTHENTICATED\",\"message\":\"로그인이 필요합니다.\"}");
	}
}
