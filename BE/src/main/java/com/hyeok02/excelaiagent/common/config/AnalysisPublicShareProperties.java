package com.hyeok02.excelaiagent.common.config;

import java.time.Duration;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.analysis-public-share")
public record AnalysisPublicShareProperties(Duration ttl) {

	private static final Duration DEFAULT_TTL = Duration.ofDays(7);

	public AnalysisPublicShareProperties {
		if (ttl == null || ttl.isZero() || ttl.isNegative()) {
			ttl = DEFAULT_TTL;
		}
	}
}
