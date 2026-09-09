package com.hyeok02.excelaiagent.telegram.error;

import java.time.Instant;
import java.util.Map;

import com.hyeok02.excelaiagent.common.error.ApiError;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class TelegramExceptionHandler {

	@ExceptionHandler(TelegramNotConfiguredException.class)
	public ResponseEntity<ApiError> handleNotConfigured(
			TelegramNotConfiguredException exception, HttpServletRequest request) {
		return response(HttpStatus.SERVICE_UNAVAILABLE, "TELEGRAM_NOT_CONFIGURED",
				exception.getMessage(), request);
	}

	@ExceptionHandler(TelegramDeliveryException.class)
	public ResponseEntity<ApiError> handleDeliveryFailure(
			TelegramDeliveryException exception, HttpServletRequest request) {
		return response(HttpStatus.BAD_GATEWAY, "TELEGRAM_DELIVERY_FAILED",
				exception.getMessage(), request);
	}

	private ResponseEntity<ApiError> response(
			HttpStatus status, String code, String message, HttpServletRequest request) {
		ApiError body = new ApiError(
				Instant.now(), status.value(), code, message,
				request.getRequestURI(), Map.of());
		return ResponseEntity.status(status).body(body);
	}
}
