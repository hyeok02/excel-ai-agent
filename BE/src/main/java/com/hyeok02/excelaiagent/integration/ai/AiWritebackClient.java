package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import tools.jackson.databind.json.JsonMapper;

@Component
public class AiWritebackClient {
	private final RestClient restClient;
	private final JsonMapper jsonMapper;

	public AiWritebackClient(RestClient aiServiceRestClient, JsonMapper jsonMapper) {
		this.restClient = aiServiceRestClient;
		this.jsonMapper = jsonMapper;
	}

	public AiWritebackProposal propose(Resource file, String instruction) {
		MultiValueMap<String, Object> body = multipart(file);
		body.add("instruction", instruction);
		try {
			AiWritebackProposal response = restClient.post()
					.uri("/api/v1/workbooks/writeback-proposals")
					.contentType(MediaType.MULTIPART_FORM_DATA)
					.body(body).retrieve().body(AiWritebackProposal.class);
			if (response == null) throw new AiServiceUnavailableException();
			return response;
		}
		catch (RestClientException exception) {
			throw new AiServiceUnavailableException(exception);
		}
	}

	public AiWritebackPackage apply(Resource file, List<AiWritebackProposal.Change> changes) {
		MultiValueMap<String, Object> body = multipart(file);
		body.add("changes", jsonMapper.writeValueAsString(
				changes.stream().map(AiWritebackApplyChange::from).toList()));
		try {
			byte[] response = restClient.post().uri("/api/v1/workbooks/writebacks/apply")
					.contentType(MediaType.MULTIPART_FORM_DATA)
					.body(body).retrieve().body(byte[].class);
			if (response == null) throw new AiServiceUnavailableException();
			return new AiWritebackArchiveReader(jsonMapper).read(response);
		}
		catch (RestClientException exception) {
			throw new AiServiceUnavailableException(exception);
		}
	}

	private MultiValueMap<String, Object> multipart(Resource file) {
		MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
		body.add("file", AiMultipartFile.named(file));
		return body;
	}
}
