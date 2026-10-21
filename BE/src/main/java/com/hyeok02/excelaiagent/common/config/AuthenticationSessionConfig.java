package com.hyeok02.excelaiagent.common.config;

import java.util.List;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.web.authentication.session.ChangeSessionIdAuthenticationStrategy;
import org.springframework.security.web.authentication.session.CompositeSessionAuthenticationStrategy;
import org.springframework.security.web.authentication.session.SessionAuthenticationStrategy;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfAuthenticationStrategy;

/** 비밀번호 로그인과 보안 필터가 동일한 세션·CSRF 전환 정책을 사용한다. */
@Configuration
public class AuthenticationSessionConfig {

	@Bean
	CookieCsrfTokenRepository csrfTokenRepository() {
		CookieCsrfTokenRepository repository = CookieCsrfTokenRepository.withHttpOnlyFalse();
		repository.setHeaderName("X-XSRF-TOKEN");
		repository.setCookieCustomizer(cookie -> cookie.path("/").sameSite("Lax"));
		return repository;
	}

	@Bean
	ChangeSessionIdAuthenticationStrategy sessionFixationProtectionStrategy() {
		return new ChangeSessionIdAuthenticationStrategy();
	}

	@Bean
	CsrfAuthenticationStrategy csrfAuthenticationStrategy(CookieCsrfTokenRepository repository) {
		CsrfAuthenticationStrategy strategy = new CsrfAuthenticationStrategy(repository);
		strategy.setRequestHandler(new SpaCsrfTokenRequestHandler());
		return strategy;
	}

	@Bean
	SessionAuthenticationStrategy loginSessionAuthenticationStrategy(
			AuthProperties properties,
			ChangeSessionIdAuthenticationStrategy sessionFixationProtectionStrategy,
			CsrfAuthenticationStrategy csrfAuthenticationStrategy) {
		return new CompositeSessionAuthenticationStrategy(properties.securityEnabled()
				? List.of(sessionFixationProtectionStrategy, csrfAuthenticationStrategy)
				: List.of(sessionFixationProtectionStrategy));
	}
}
