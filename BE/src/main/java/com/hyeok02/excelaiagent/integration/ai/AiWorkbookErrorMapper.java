package com.hyeok02.excelaiagent.integration.ai;

import java.util.Map;

import com.hyeok02.excelaiagent.analysis.error.UnreadableExcelFileException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

final class AiWorkbookErrorMapper {

	private static final JsonMapper JSON = JsonMapper.builder().build();
	private static final String COMPATIBILITY_MESSAGE =
			"Excel 호환 서식을 읽을 수 없습니다. 파일을 Excel에서 다시 저장한 뒤 업로드해 주세요.";

	private AiWorkbookErrorMapper() {
	}

	static RuntimeException translate(RestClientException exception) {
		if (exception instanceof RestClientResponseException response
				&& response.getStatusCode().value() == 400) {
			String body = response.getResponseBodyAsString();
			if (body.length() <= 2048) {
				try {
					Map<?, ?> error = JSON.readValue(body, Map.class);
					Object detail = error == null ? null : error.get("detail");
					if (UnreadableExcelFileException.STYLE_MESSAGE.equals(detail)
							|| COMPATIBILITY_MESSAGE.equals(detail)) {
						return new UnreadableExcelFileException();
					}
					if (UnreadableExcelFileException.INVALID_FORMAT_MESSAGE.equals(detail)) {
						return UnreadableExcelFileException.invalidFormat();
					}
				}
				catch (JacksonException ignored) {
					// Unknown or malformed upstream responses must not reach the user.
				}
			}
		}
		return new AiServiceUnavailableException(exception);
	}
}
