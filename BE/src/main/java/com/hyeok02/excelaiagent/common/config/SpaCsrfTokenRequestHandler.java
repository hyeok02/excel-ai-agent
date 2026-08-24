package com.hyeok02.excelaiagent.common.config;

import java.util.function.Supplier;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.csrf.CsrfTokenRequestHandler;
import org.springframework.security.web.csrf.XorCsrfTokenRequestAttributeHandler;
import org.springframework.util.StringUtils;

final class SpaCsrfTokenRequestHandler implements CsrfTokenRequestHandler {

	private final CsrfTokenRequestHandler plain = new CsrfTokenRequestAttributeHandler();
	private final CsrfTokenRequestHandler xor = new XorCsrfTokenRequestAttributeHandler();

	@Override
	public void handle(
			HttpServletRequest request,
			HttpServletResponse response,
			Supplier<CsrfToken> deferredCsrfToken) {
		xor.handle(request, response, deferredCsrfToken);
		deferredCsrfToken.get();
	}

	@Override
	public String resolveCsrfTokenValue(HttpServletRequest request, CsrfToken csrfToken) {
		CsrfTokenRequestHandler delegate = StringUtils.hasText(request.getHeader(csrfToken.getHeaderName()))
				? plain
				: xor;
		return delegate.resolveCsrfTokenValue(request, csrfToken);
	}
}
