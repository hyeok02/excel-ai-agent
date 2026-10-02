package com.hyeok02.excelaiagent.integration.ai;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
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

	public AiWorkbookSummary summarizeWorkbook(MultipartFile file, boolean includeHiddenSheets) {
		return summarizeWorkbook(named(file), includeHiddenSheets);
	}

	public AiWorkbookInsights generateWorkbookInsights(
			MultipartFile file, AnalysisDepth depth, boolean includeHiddenSheets) {
		return generateWorkbookInsights(named(file), depth, includeHiddenSheets);
	}

	public AiWorkbookSummary summarizeWorkbook(Resource file, boolean includeHiddenSheets) {
		return postWorkbook(file, "/api/v1/workbooks/summary", AiWorkbookSummary.class,
				null, includeHiddenSheets);
	}

	public AiWorkbookInsights generateWorkbookInsights(
			Resource file, AnalysisDepth depth, boolean includeHiddenSheets) {
		return postWorkbook(file, "/api/v1/workbooks/insights", AiWorkbookInsights.class,
				depth, includeHiddenSheets);
	}

	public AiWorkbookQuestion askWorkbook(
			Resource file, String question, boolean includeHiddenSheets) {
		MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
		body.add("file", namedFile(file));
		body.add("question", question);
		body.add("include_hidden_sheets", String.valueOf(includeHiddenSheets));
		try {
			AiWorkbookQuestion response = restClient.post()
					.uri("/api/v1/workbooks/questions")
					.contentType(MediaType.MULTIPART_FORM_DATA)
					.body(body)
					.retrieve()
					.body(AiWorkbookQuestion.class);
			if (response == null) {
				throw new AiServiceUnavailableException();
			}
			return response;
		}
		catch (RestClientException exception) {
			throw AiWorkbookErrorMapper.translate(exception);
		}
	}

	private <T> T postWorkbook(
			Resource file,
			String uri,
			Class<T> responseType,
			AnalysisDepth depth,
			boolean includeHiddenSheets) {
		MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
		body.add("file", namedFile(file));
		body.add("include_hidden_sheets", String.valueOf(includeHiddenSheets));
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
			throw AiWorkbookErrorMapper.translate(exception);
		}
	}

	private Resource named(MultipartFile file) {
		return new NamedResource(file.getResource(), file.getOriginalFilename());
	}

	private HttpEntity<Resource> namedFile(Resource file) {
		String filename = file.getFilename() == null || file.getFilename().isBlank()
				? "workbook.xlsx"
				: file.getFilename();
		HttpHeaders headers = new HttpHeaders();
		headers.setContentDisposition(ContentDisposition.formData()
				.name("file")
				.filename(filename)
				.build());
		return new HttpEntity<>(file, headers);
	}

	public record AiServiceHealth(String status, String service) {
	}
}
