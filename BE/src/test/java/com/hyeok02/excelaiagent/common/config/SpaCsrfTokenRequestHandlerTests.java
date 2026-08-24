package com.hyeok02.excelaiagent.common.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.web.csrf.DefaultCsrfToken;

class SpaCsrfTokenRequestHandlerTests {

	@Test
	void resolvesRawCookieTokenFromSpaRequestHeader() {
		SpaCsrfTokenRequestHandler handler = new SpaCsrfTokenRequestHandler();
		MockHttpServletRequest request = new MockHttpServletRequest();
		request.addHeader("X-XSRF-TOKEN", "raw-cookie-token");
		DefaultCsrfToken csrfToken = new DefaultCsrfToken(
				"X-XSRF-TOKEN", "_csrf", "raw-cookie-token");

		String resolvedToken = handler.resolveCsrfTokenValue(request, csrfToken);

		assertEquals("raw-cookie-token", resolvedToken);
	}
}
