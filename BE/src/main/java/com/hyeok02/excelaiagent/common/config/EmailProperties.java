package com.hyeok02.excelaiagent.common.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.email")
public record EmailProperties(boolean enabled, String fromAddress) {

	public EmailProperties {
		fromAddress = fromAddress == null ? "" : fromAddress.trim();
	}

	public boolean configured() {
		return enabled && !fromAddress.isBlank();
	}
}
