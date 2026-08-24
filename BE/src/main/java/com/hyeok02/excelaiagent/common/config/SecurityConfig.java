package com.hyeok02.excelaiagent.common.config;

import java.io.IOException;

import com.hyeok02.excelaiagent.auth.application.CompanyOidcUserService;
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
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;

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
			CompanyOidcUserService companyOidcUserService) throws Exception {
		CookieCsrfTokenRepository csrfRepository = CookieCsrfTokenRepository.withHttpOnlyFalse();
		csrfRepository.setHeaderName("X-XSRF-TOKEN");
		csrfRepository.setCookieCustomizer(cookie -> cookie.path("/").sameSite("Lax"));

		http
				.cors(Customizer.withDefaults())
				.exceptionHandling(exceptions -> exceptions
						.authenticationEntryPoint((request, response, exception) ->
								writeUnauthorized(response)))
				.logout(logout -> logout.disable());

		if (authProperties.securityEnabled()) {
			http.csrf(csrf -> csrf
					.csrfTokenRepository(csrfRepository)
					.csrfTokenRequestHandler(new SpaCsrfTokenRequestHandler()))
					.authorizeHttpRequests(authorize -> authorize
					.requestMatchers(
							"/health", "/actuator/health/**", "/v3/api-docs/**",
							"/swagger-ui/**", "/swagger-ui.html", "/oauth2/**", "/login/oauth2/**")
						.permitAll()
					.requestMatchers(HttpMethod.GET,
							"/api/v1/auth/me", "/api/v1/auth/config", "/api/v1/auth/csrf")
						.permitAll()
					.requestMatchers(HttpMethod.POST, "/api/v1/auth/login").permitAll()
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
