package com.hyeok02.excelaiagent.common.error;

import java.util.UUID;

import jakarta.servlet.http.HttpServletRequest;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 어느 핸들러도 잡지 않은 예외를 받아, 다른 오류와 같은 형식으로 응답한다.
 *
 * 지금까지는 예상 못 한 예외가 스프링 기본 오류 처리로 빠져, 프런트엔드가
 * 쓰는 ApiError 형식이 아닌 응답이 나갔다. 서버 로그에도 어느 요청이
 * 터졌는지 묶어 볼 단서가 남지 않았다.
 *
 * 가장 낮은 우선순위로 둬야 한다. 그러지 않으면 Exception 하나로 다른
 * 핸들러들이 맡은 예외까지 먼저 가로채, 400이어야 할 응답이 500이 된다.
 */
@Order(Ordered.LOWEST_PRECEDENCE)
@RestControllerAdvice
public class UnexpectedExceptionHandler {

	private static final Logger log = LoggerFactory.getLogger(UnexpectedExceptionHandler.class);

	@ExceptionHandler(Exception.class)
	public ResponseEntity<ApiError> handleUnexpected(
			Exception exception, HttpServletRequest request) throws Exception {
		// 인증·인가 예외는 스프링 시큐리티가 401·403으로 처리해야 한다.
		if (exception instanceof AccessDeniedException
				|| exception instanceof AuthenticationException) {
			throw exception;
		}
		String traceId = UUID.randomUUID().toString();
		log.error("처리되지 않은 예외 traceId={} {} {}",
				traceId, request.getMethod(), request.getRequestURI(), exception);
		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(ApiError.of(
				HttpStatus.INTERNAL_SERVER_ERROR.value(), "INTERNAL_ERROR",
				"요청을 처리하지 못했습니다. 문제가 계속되면 관리자에게 코드 "
						+ traceId + " 를 알려주세요.",
				request.getRequestURI()));
	}
}
