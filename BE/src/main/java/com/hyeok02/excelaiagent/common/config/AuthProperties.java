package com.hyeok02.excelaiagent.common.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.auth")
public record AuthProperties(
		boolean securityEnabled,
		String frontendBaseUrl,
		Bootstrap bootstrap,
		Sso sso) {

	public AuthProperties {
		frontendBaseUrl = frontendBaseUrl == null || frontendBaseUrl.isBlank()
				? "http://localhost:5173"
				: frontendBaseUrl.replaceAll("/+$", "");
		bootstrap = bootstrap == null
				? new Bootstrap("admin", "", "System Administrator")
				: bootstrap;
		sso = sso == null ? new Sso(false, "company", "", true) : sso;
	}

	public record Bootstrap(String username, String password, String displayName) {
		public Bootstrap {
			username = username == null || username.isBlank() ? "admin" : username;
			// 비밀번호에는 기본값을 두지 않는다. 기본값이 있으면 설정을 잊은 배포가
			// 문서에 적힌 자격증명으로 그대로 떠 있게 된다.
			password = password == null ? "" : password;
			displayName = displayName == null || displayName.isBlank()
					? "System Administrator"
					: displayName;
		}
	}

	public record Sso(
			boolean enabled,
			String registrationId,
			String allowedDomain,
			boolean autoProvision) {
		public Sso {
			registrationId = registrationId == null || registrationId.isBlank()
					? "company"
					: registrationId;
			allowedDomain = allowedDomain == null ? "" : allowedDomain.trim().toLowerCase();
		}
	}
}
