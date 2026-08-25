package com.hyeok02.excelaiagent.integration.ai;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

abstract class AiServiceClientTestSupport {
	protected MockRestServiceServer server;
	protected AiServiceClient client;

	@BeforeEach
	void setUp() {
		RestClient.Builder builder = RestClient.builder().baseUrl("http://localhost:8000");
		server = MockRestServiceServer.bindTo(builder).build();
		client = new AiServiceClient(builder.build());
	}

	protected MockMultipartFile workbook() {
		return new MockMultipartFile("file", "sales.xlsx", "application/octet-stream",
				new byte[] {0x50, 0x4b, 0x03, 0x04});
	}

	protected String fixture(String filename) {
		try (var stream = getClass().getResourceAsStream("/ai/" + filename)) {
			if (stream == null) {
				throw new IllegalArgumentException("테스트 fixture를 찾을 수 없습니다: " + filename);
			}
			return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
		}
		catch (IOException exception) {
			throw new IllegalStateException("테스트 fixture를 읽지 못했습니다.", exception);
		}
	}
}
