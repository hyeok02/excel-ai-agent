package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisDepth;
import com.hyeok02.excelaiagent.analysis.error.UnreadableExcelFileException;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.MethodSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import tools.jackson.databind.json.JsonMapper;

class AiWorkbookFileErrorClientTests extends AiServiceClientTestSupport {

	@ParameterizedTest
	@MethodSource("safeFileErrors")
	void mapsOnlyKnownFileErrorsToUserActionableExceptions(
			Endpoint endpoint, String upstreamMessage, String userMessage) {
		server.expect(requestTo(endpoint.url()))
				.andRespond(withStatus(HttpStatus.BAD_REQUEST)
						.contentType(MediaType.APPLICATION_JSON)
						.body("{\"detail\":\"" + upstreamMessage + "\"}"));

		assertThatThrownBy(() -> invoke(endpoint))
				.isInstanceOf(UnreadableExcelFileException.class)
				.hasMessage(userMessage)
				.hasNoCause();
		server.verify();
	}

	@ParameterizedTest
	@MethodSource("unsafeResponses")
	void doesNotExposeUnknownOrMalformedUpstreamBodies(Endpoint endpoint, String body) {
		server.expect(requestTo(endpoint.url()))
				.andRespond(withStatus(HttpStatus.BAD_REQUEST)
						.contentType(MediaType.APPLICATION_JSON).body(body));

		assertThatThrownBy(() -> invoke(endpoint))
				.isInstanceOf(AiServiceUnavailableException.class)
				.hasMessage("AI Service에 연결할 수 없습니다.");
		server.verify();
	}

	@ParameterizedTest
	@EnumSource(Endpoint.class)
	void keepsServerFailuresAsServiceUnavailableEvenWithKnownFileMessage(Endpoint endpoint) {
		server.expect(requestTo(endpoint.url()))
				.andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
						.contentType(MediaType.APPLICATION_JSON)
						.body("{\"detail\":\"" + UnreadableExcelFileException.STYLE_MESSAGE + "\"}"));

		assertThatThrownBy(() -> invoke(endpoint))
				.isInstanceOf(AiServiceUnavailableException.class);
		server.verify();
	}

	@ParameterizedTest
	@EnumSource(Endpoint.class)
	void keepsConnectionFailuresAsServiceUnavailable(Endpoint endpoint) {
		server.expect(requestTo(endpoint.url()))
				.andRespond(withException(new IOException("private connection detail")));

		assertThatThrownBy(() -> invoke(endpoint))
				.isInstanceOf(AiServiceUnavailableException.class)
				.hasMessage("AI Service에 연결할 수 없습니다.");
		server.verify();
	}

	private void invoke(Endpoint endpoint) {
		var file = workbook().getResource();
		switch (endpoint) {
			case SUMMARY -> client.summarizeWorkbook(file);
			case INSIGHTS -> client.generateWorkbookInsights(file, AnalysisDepth.AUTO);
			case QUESTIONS -> client.askWorkbook(file, "합계를 알려줘");
			case PROPOSE -> new AiWritebackClient(restClient, JsonMapper.builder().build())
					.propose(file, "B2를 12로 수정");
			case APPLY -> new AiWritebackClient(restClient, JsonMapper.builder().build())
					.apply(file, List.of());
		}
	}

	private static Stream<Arguments> safeFileErrors() {
		return Arrays.stream(Endpoint.values()).flatMap(endpoint -> Stream.of(
				Arguments.of(endpoint, UnreadableExcelFileException.STYLE_MESSAGE,
						UnreadableExcelFileException.STYLE_MESSAGE),
				Arguments.of(endpoint,
						"Excel 호환 서식을 읽을 수 없습니다. 파일을 Excel에서 다시 저장한 뒤 업로드해 주세요.",
						UnreadableExcelFileException.STYLE_MESSAGE),
				Arguments.of(endpoint, UnreadableExcelFileException.INVALID_FORMAT_MESSAGE,
						UnreadableExcelFileException.INVALID_FORMAT_MESSAGE)));
	}

	private static Stream<Arguments> unsafeResponses() {
		return Arrays.stream(Endpoint.values()).flatMap(endpoint -> Stream.of(
				"{\"detail\":\"private api_key=secret /srv/uploads/file.xlsx\"}",
				"<html>private traceback</html>", "null", "[]",
				"{\"detail\":{\"private\":\"secret\"}}",
				"{\"detail\":\"" + "private".repeat(400) + "\"}")
				.map(body -> Arguments.of(endpoint, body)));
	}

	private enum Endpoint {
		SUMMARY("summary"), INSIGHTS("insights"), QUESTIONS("questions"),
		PROPOSE("writeback-proposals"), APPLY("writebacks/apply");

		private final String path;
		Endpoint(String path) { this.path = path; }
		String url() { return "http://localhost:8000/api/v1/workbooks/" + path; }
	}
}
