package com.hyeok02.excelaiagent.telegram.integration;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.time.Duration;

import com.hyeok02.excelaiagent.common.config.TelegramProperties;
import com.hyeok02.excelaiagent.telegram.error.TelegramNotConfiguredException;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class TelegramClientTests {

	@Test
	void sendsPlainTextToConfiguredChat() {
		RestClient.Builder builder = RestClient.builder().baseUrl("https://api.telegram.test");
		MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
		TelegramClient client = new TelegramClient(builder.build(), properties(true));
		server.expect(once(), requestTo("https://api.telegram.test/botdemo-token/sendMessage"))
				.andExpect(method(POST))
				.andExpect(content().string(containsString("\"chat_id\":\"12345\"")))
				.andExpect(content().string(containsString("Excel 분석 완료")))
				.andRespond(withSuccess("{\"ok\":true}", MediaType.APPLICATION_JSON));

		client.sendMessage("Excel 분석 완료");

		server.verify();
	}

	@Test
	void rejectsDeliveryWhenTelegramIsNotConfigured() {
		TelegramClient client = new TelegramClient(RestClient.create(), properties(false));

		assertThatThrownBy(() -> client.sendMessage("Excel 분석 완료"))
				.isInstanceOf(TelegramNotConfiguredException.class);
	}

	private TelegramProperties properties(boolean enabled) {
		return new TelegramProperties(
				enabled, "demo-token", "12345", "https://api.telegram.test",
				Duration.ofSeconds(1), Duration.ofSeconds(1));
	}
}
