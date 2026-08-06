package com.hyeok02.excelaiagent.common.config;

import java.time.Duration;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.util.unit.DataSize;

@ConfigurationProperties(prefix = "app")
public record AppProperties(Cors cors, AiService aiService, Analysis analysis, Storage storage) {

	public AppProperties {
		cors = cors == null ? new Cors(List.of("http://localhost:5173")) : cors;
		aiService = aiService == null
				? new AiService("http://localhost:8000", Duration.ofSeconds(3), Duration.ofSeconds(60))
				: aiService;
		analysis = analysis == null ? new Analysis(DataSize.ofMegabytes(50)) : analysis;
		storage = storage == null ? new Storage("./uploads") : storage;
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

	public record Analysis(DataSize maxFileSize) {

		public Analysis {
			maxFileSize = maxFileSize == null ? DataSize.ofMegabytes(50) : maxFileSize;
		}
	}

	public record Storage(String uploadDir) {

		public Storage {
			uploadDir = uploadDir == null || uploadDir.isBlank() ? "./uploads" : uploadDir;
		}
	}
}
