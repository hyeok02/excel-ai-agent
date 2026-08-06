package com.hyeok02.excelaiagent.common.config;

import java.time.Duration;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public record AppProperties(Cors cors, AiService aiService) {

	public AppProperties {
		cors = cors == null ? new Cors(List.of("http://localhost:5173")) : cors;
		aiService = aiService == null
				? new AiService("http://localhost:8000", Duration.ofSeconds(3), Duration.ofSeconds(60))
				: aiService;
	}

	public record Cors(List<String> allowedOrigins) {

		public Cors {
			allowedOrigins = allowedOrigins == null || allowedOrigins.isEmpty()
					? List.of("http://localhost:5173")
					: List.copyOf(allowedOrigins);
		}
	}

	public record AiService(String baseUrl, Duration connectTimeout, Duration readTimeout) {
	}
}
