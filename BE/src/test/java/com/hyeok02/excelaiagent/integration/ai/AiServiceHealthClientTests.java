package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.http.HttpMethod.GET;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

class AiServiceHealthClientTests extends AiServiceClientTestSupport {
	@Test
	void returnsFastApiHealthResponse() {
		server.expect(once(), requestTo("http://localhost:8000/health"))
				.andExpect(method(GET))
				.andRespond(withSuccess(
						"{\"status\":\"UP\",\"service\":\"excel-ai-agent-service\"}",
						MediaType.APPLICATION_JSON));
		AiServiceClient.AiServiceHealth response = client.checkHealth();
		assertThat(response.status()).isEqualTo("UP");
		assertThat(response.service()).isEqualTo("excel-ai-agent-service");
		server.verify();
	}

	@Test
	void throwsUnavailableExceptionWhenFastApiReturnsError() {
		server.expect(once(), requestTo("http://localhost:8000/health"))
				.andExpect(method(GET)).andRespond(withServerError());
		assertThatThrownBy(client::checkHealth).isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}
}
