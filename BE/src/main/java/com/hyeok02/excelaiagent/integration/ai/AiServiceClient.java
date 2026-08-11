package com.hyeok02.excelaiagent.integration.ai;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class AiServiceClient {

	private final RestClient restClient;

	public AiServiceClient(RestClient aiServiceRestClient) {
		this.restClient = aiServiceRestClient;
	}

	public AiServiceHealth checkHealth() {
		try {
			AiServiceHealth response = restClient.get()
					.uri("/health")
					.retrieve()
					.body(AiServiceHealth.class);

			if (response == null || !"UP".equals(response.status())) {
				throw new AiServiceUnavailableException();
			}
			return response;
		}
		catch (RestClientException exception) {
			throw new AiServiceUnavailableException(exception);
		}
	}

	public record AiServiceHealth(String status, String service) {
	}
}
