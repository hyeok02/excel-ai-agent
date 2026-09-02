package com.hyeok02.excelaiagent.health.api;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(
		classes = BackendApplication.class,
		properties = "app.storage.upload-dir=build/test-uploads")
@AutoConfigureMockMvc
class AiServiceHealthControllerTests {

	@Autowired
	private MockMvc mockMvc;

	@MockitoBean
	private AiServiceClient aiServiceClient;

	@Test
	void returnsAiServiceHealth() throws Exception {
		when(aiServiceClient.checkHealth())
				.thenReturn(new AiServiceClient.AiServiceHealth("UP", "excel-ai-agent-service"));

		mockMvc.perform(get("/api/v1/health/ai-service"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("UP"))
				.andExpect(jsonPath("$.service").value("excel-ai-agent-service"))
				.andExpect(jsonPath("$.timestamp").isNotEmpty());
	}

	@Test
	void returnsServiceUnavailableWhenAiServiceCannotBeReached() throws Exception {
		when(aiServiceClient.checkHealth()).thenThrow(new AiServiceUnavailableException());

		mockMvc.perform(get("/api/v1/health/ai-service"))
				.andExpect(status().isServiceUnavailable())
				.andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"))
				.andExpect(jsonPath("$.message")
						.value("AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요."));
	}
}
