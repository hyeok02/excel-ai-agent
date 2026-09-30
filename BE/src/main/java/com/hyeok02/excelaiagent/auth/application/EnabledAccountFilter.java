package com.hyeok02.excelaiagent.auth.application;

import java.io.IOException;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/** Rejects an already authenticated session as soon as its backing account is disabled. */
public final class EnabledAccountFilter extends OncePerRequestFilter {

	private final UserAccountService userAccountService;

	public EnabledAccountFilter(UserAccountService userAccountService) {
		this.userAccountService = userAccountService;
	}

	@Override
	protected boolean shouldNotFilter(HttpServletRequest request) {
		String requestUri = request.getRequestURI();
		String contextPath = request.getContextPath();
		String path = contextPath.isEmpty() ? requestUri : requestUri.substring(contextPath.length());
		if (!path.startsWith("/api/v1/")) {
			return true;
		}
		return path.equals("/api/v1/auth/login")
				|| path.equals("/api/v1/auth/logout")
				|| path.equals("/api/v1/auth/config")
				|| path.equals("/api/v1/auth/csrf")
				|| path.startsWith("/api/v1/public/")
				|| path.equals("/api/v1/telegram/webhook");
	}

	@Override
	protected void doFilterInternal(
			HttpServletRequest request,
			HttpServletResponse response,
			FilterChain filterChain) throws ServletException, IOException {
		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (authentication != null && authentication.isAuthenticated()
				&& !"anonymousUser".equals(authentication.getPrincipal())
				&& !userAccountService.isAuthenticationEnabled(authentication)) {
			SecurityContextHolder.clearContext();
			HttpSession session = request.getSession(false);
			if (session != null) {
				try {
					session.invalidate();
				}
				catch (IllegalStateException ignored) {
					// Another concurrent request already invalidated the same session.
				}
			}
			writeDisabledResponse(response);
			return;
		}
		filterChain.doFilter(request, response);
	}

	private static void writeDisabledResponse(HttpServletResponse response) throws IOException {
		response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		response.setCharacterEncoding("UTF-8");
		response.getWriter().write(
				"{\"status\":401,\"code\":\"ACCOUNT_DISABLED\","
						+ "\"message\":\"비활성화된 계정입니다.\"}");
	}
}
