package com.hyeok02.excelaiagent.integration.ai;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import org.springframework.http.MediaType;
import org.springframework.core.io.Resource;
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
		return summarizeWorkbook(file.getResource());
	}

	public AiWorkbookInsights generateWorkbookInsights(MultipartFile file, AnalysisDepth depth) {
		return generateWorkbookInsights(file.getResource(), depth);
	}

	public AiWorkbookSummary summarizeWorkbook(Resource file) {
		return postWorkbook(file, "/api/v1/workbooks/summary", AiWorkbookSummary.class, null);
	}

	public AiWorkbookInsights generateWorkbookInsights(Resource file, AnalysisDepth depth) {
		return postWorkbook(file, "/api/v1/workbooks/insights", AiWorkbookInsights.class, depth);
	}

	private <T> T postWorkbook(
			Resource file,
			String uri,
			Class<T> responseType,
			AnalysisDepth depth) {
		MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
		body.add("file", file);
		if (depth != null) {
			body.add("depth", depth.name());
		}
		try {
			T response = restClient.post()
					.uri(uri)
					.contentType(MediaType.MULTIPART_FORM_DATA)
					.body(body)
					.retrieve()
					.body(responseType);

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
