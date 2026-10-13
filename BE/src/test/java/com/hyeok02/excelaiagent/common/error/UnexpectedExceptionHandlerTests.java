package com.hyeok02.excelaiagent.common.error;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.access.AccessDeniedException;

class UnexpectedExceptionHandlerTests {

	private final UnexpectedExceptionHandler handler = new UnexpectedExceptionHandler();

	@Test
	void answersUnexpectedFailuresInTheSharedErrorShape() throws Exception {
		MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/analyses");

		ResponseEntity<ApiError> response = handler.handleUnexpected(
				new IllegalArgumentException("경계 조건을 놓쳤다"), request);

		assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
		ApiError body = response.getBody();
		assertThat(body).isNotNull();
		assertThat(body.code()).isEqualTo("INTERNAL_ERROR");
		assertThat(body.path()).isEqualTo("/api/v1/analyses");
		// 메시지에 예외 내용을 담지 않고, 로그와 맞춰 볼 코드만 남긴다.
		assertThat(body.message()).doesNotContain("경계 조건을 놓쳤다");
	}

	@Test
	void letsSpringSecurityHandleAuthorizationFailures() {
		MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/admin/users");
		AccessDeniedException denied = new AccessDeniedException("권한 없음");

		assertThat(thrownBy(denied, request)).isSameAs(denied);
	}

	private Throwable thrownBy(Exception exception, MockHttpServletRequest request) {
		try {
			handler.handleUnexpected(exception, request);
			return null;
		}
		catch (Exception thrown) {
			return thrown;
		}
	}
}
