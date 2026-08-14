package com.hyeok02.excelaiagent.integration.ai;

import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.multipart.MultipartFile;

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

	public AiWorkbookSummary summarizeWorkbook(MultipartFile file) {
		MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
		body.add("file", file.getResource());

		try {
			AiWorkbookSummary response = restClient.post()
					.uri("/api/v1/workbooks/summary")
					.contentType(MediaType.MULTIPART_FORM_DATA)
					.body(body)
					.retrieve()
					.body(AiWorkbookSummary.class);

			if (response == null) {
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
