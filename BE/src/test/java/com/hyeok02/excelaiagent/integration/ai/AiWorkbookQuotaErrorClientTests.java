package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

import java.util.stream.Stream;
import com.hyeok02.excelaiagent.common.error.AnalysisExceptionHandler;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletRequest;

class AiWorkbookQuotaErrorClientTests extends AiServiceClientTestSupport {
	@Test
	void preservesOnlyTheAllowlistedQuotaMessageThroughTheUserResponse() {
		var error = invoke(502, "{\"detail\":\"" + AiServiceUnavailableException.QUOTA_MESSAGE + "\"}");
		assertThat(error.getMessage()).isEqualTo(AiServiceUnavailableException.QUOTA_MESSAGE);
		assertThat(error.getCause()).isNull();
		var response = new AnalysisExceptionHandler().handleAiServiceUnavailable(
				error, new MockHttpServletRequest("POST", "/api/v1/analyses/id/questions"));
		assertThat(response.getStatusCode()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE);
		assertThat(response.getBody().message()).isEqualTo(AiServiceUnavailableException.QUOTA_MESSAGE);
	}

	@ParameterizedTest
	@ValueSource(ints = {400, 429, 500, 503})
	void quotaTextOnOtherStatusesKeepsTheGenericMapping(int status) {
		var error = invoke(status, "{\"detail\":\"" + AiServiceUnavailableException.QUOTA_MESSAGE + "\"}");
		assertThat(error.userMessage()).isEqualTo("AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요.");
	}

	@ParameterizedTest
	@MethodSource("unsafeBodies")
	void unknownMalformedAndSecretBodiesAreNeverPassedToTheUser(String body) {
		var error = invoke(502, body);
		var response = new AnalysisExceptionHandler().handleAiServiceUnavailable(
				error, new MockHttpServletRequest("POST", "/api/v1/analyses/id/questions"));
		assertThat(response.getBody().message())
				.isEqualTo("AI 응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요.")
				.doesNotContain("secret", "/srv/", "traceback");
	}

	private AiServiceUnavailableException invoke(int status, String body) {
		server.expect(requestTo("http://localhost:8000/api/v1/workbooks/questions"))
				.andRespond(withStatus(HttpStatus.valueOf(status)).contentType(MediaType.APPLICATION_JSON).body(body));
		var error = assertThrows(AiServiceUnavailableException.class,
				() -> client.askWorkbook(workbook().getResource(), "합계를 알려줘", false));
		server.verify();
		return error;
	}

	private static Stream<String> unsafeBodies() {
		return Stream.of("{\"detail\":\"private api_key=secret /srv/uploads/file.xlsx\"}",
				"<html>private traceback</html>", "null", "[]", "{\"detail\":{\"secret\":true}}",
				"{\"detail\":\"" + AiServiceUnavailableException.QUOTA_MESSAGE + " secret\"}",
				"{\"detail\":\"" + "secret".repeat(400) + "\"}");
	}
}
