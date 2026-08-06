package com.hyeok02.excelaiagent.health.api;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class HealthControllerTests {

	private final HealthController controller = new HealthController();

	@Test
	void returnsUpStatus() {
		HealthController.HealthResponse response = controller.health();

		assertThat(response.status()).isEqualTo("UP");
		assertThat(response.service()).isEqualTo("excel-ai-agent-backend");
		assertThat(response.timestamp()).isNotNull();
	}
}
