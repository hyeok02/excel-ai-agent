package com.hyeok02.excelaiagent.auth.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verifyNoInteractions;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import com.hyeok02.excelaiagent.BackendApplication;
import com.hyeok02.excelaiagent.integration.ai.AiServiceClient;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackClient;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.web.servlet.function.RouterFunction;
import org.springframework.web.servlet.function.RouterFunctions;
import org.springframework.web.servlet.function.ServerResponse;

@SpringBootTest(classes = BackendApplication.class,
		webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
				"app.auth.security-enabled=true", "app.auth.sso.enabled=false",
				"app.storage.upload-dir=build/test-auth-http-uploads",
				"spring.datasource.url=jdbc:h2:mem:session-http;MODE=PostgreSQL;DB_CLOSE_DELAY=-1;DATABASE_TO_LOWER=TRUE"
		})
@Import(AuthenticationSessionHttpTests.SessionFixture.class)
class AuthenticationSessionHttpTests {
	@LocalServerPort private int port;
	@MockitoBean private AiServiceClient aiServiceClient;
	@MockitoBean private AiWritebackClient aiWritebackClient;
	private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

	@Test
	void rotatesRealSessionAndCsrfCookiesAndRevokesAccessOnLogout() throws Exception {
		var before = request("GET", "/v3/api-docs/session-fixture", "", null, "");
		assertThat(before.statusCode()).isEqualTo(200);
		String oldSession = cookie(before, "JSESSIONID");
		String oldCsrf = cookie(before, "XSRF-TOKEN");
		var login = request("POST", "/api/v1/auth/login", oldSession + "; " + oldCsrf,
				value(oldCsrf), "{\"username\":\"admin\",\"password\":\"admin1234\"}");
		assertThat(login.statusCode()).isEqualTo(200);
		String session = cookie(login, "JSESSIONID");
		String csrf = cookie(login, "XSRF-TOKEN");
		assertThat(session).isNotEqualTo(oldSession);
		assertThat(csrf).isNotEqualTo(oldCsrf);

		assertThat(request("GET", "/api/v1/analyses", oldSession, null, "").statusCode()).isEqualTo(401);
		assertThat(request("GET", "/api/v1/auth/me", oldSession, null, "").statusCode()).isEqualTo(204);
		var currentUser = request("GET", "/api/v1/auth/me", session, null, "");
		assertThat(currentUser.statusCode()).isEqualTo(200);
		assertThat(currentUser.body()).contains("\"username\":\"admin\"");
		assertThat(request("GET", "/api/v1/analyses", session, null, "").statusCode()).isEqualTo(200);
		assertThat(request("POST", "/api/v1/auth/logout", session + "; " + csrf,
				value(oldCsrf), "").statusCode()).isEqualTo(403);
		assertThat(request("POST", "/api/v1/auth/logout", session + "; " + csrf,
				value(csrf), "").statusCode()).isEqualTo(204);
		assertThat(request("GET", "/api/v1/analyses", session, null, "").statusCode()).isEqualTo(401);
		assertThat(request("GET", "/api/v1/auth/me", session, null, "").statusCode()).isEqualTo(204);
		verifyNoInteractions(aiServiceClient, aiWritebackClient);
	}

	private HttpResponse<String> request(String method, String route, String cookies, String csrf, String body)
			throws Exception {
		var request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + route))
				.timeout(Duration.ofSeconds(10)).header("Content-Type", "application/json")
				.method(method, HttpRequest.BodyPublishers.ofString(body));
		if (!cookies.isBlank()) request.header("Cookie", cookies);
		if (csrf != null) request.header("X-XSRF-TOKEN", csrf);
		return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
	}

	private String cookie(HttpResponse<?> response, String name) {
		return response.headers().allValues("set-cookie").stream()
				.map(header -> header.split(";", 2)[0])
				.filter(header -> header.startsWith(name + "=") && !value(header).isBlank())
				.reduce((first, last) -> last).orElseThrow();
	}

	private String value(String cookie) {
		return cookie.substring(cookie.indexOf('=') + 1);
	}

	@TestConfiguration(proxyBeanMethods = false)
	static class SessionFixture {
		@Bean
		RouterFunction<ServerResponse> anonymousSessionFixture() {
			return RouterFunctions.route().GET("/v3/api-docs/session-fixture", request -> {
				request.servletRequest().getSession(true);
				return ServerResponse.ok().body("anonymous session created");
			}).build();
		}
	}
}
