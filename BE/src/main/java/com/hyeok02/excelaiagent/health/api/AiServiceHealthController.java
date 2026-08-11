package com.hyeok02.excelaiagent.health.api;

import java.time.Instant;

import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/health/ai-service")
public class AiServiceHealthController {

	private final AiServiceClient aiServiceClient;

	public AiServiceHealthController(AiServiceClient aiServiceClient) {
		this.aiServiceClient = aiServiceClient;
	}

	@GetMapping
	public AiServiceHealthResponse health() {
		AiServiceClient.AiServiceHealth health = aiServiceClient.checkHealth();
		return new AiServiceHealthResponse(health.status(), health.service(), Instant.now());
	}

	public record AiServiceHealthResponse(String status, String service, Instant timestamp) {
	}
}
