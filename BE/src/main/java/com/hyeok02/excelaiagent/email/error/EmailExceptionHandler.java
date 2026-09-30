package com.hyeok02.excelaiagent.email.error;

import com.hyeok02.excelaiagent.common.error.ApiError;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class EmailExceptionHandler {

	@ExceptionHandler(EmailNotConfiguredException.class)
	public ResponseEntity<ApiError> handleNotConfigured(
			EmailNotConfiguredException exception, HttpServletRequest request) {
		return response(HttpStatus.SERVICE_UNAVAILABLE, "EMAIL_NOT_CONFIGURED",
				exception, request);
	}

	@ExceptionHandler(EmailDeliveryException.class)
	public ResponseEntity<ApiError> handleDeliveryFailure(
			EmailDeliveryException exception, HttpServletRequest request) {
		return response(HttpStatus.BAD_GATEWAY, "EMAIL_DELIVERY_FAILED",
				exception, request);
	}

	@ExceptionHandler(EmailRecipientNotFoundException.class)
	public ResponseEntity<ApiError> handleRecipientNotFound(
			EmailRecipientNotFoundException exception, HttpServletRequest request) {
		return response(HttpStatus.NOT_FOUND, "EMAIL_RECIPIENT_NOT_FOUND",
				exception, request);
	}

	@ExceptionHandler(DuplicateEmailRecipientException.class)
	public ResponseEntity<ApiError> handleDuplicateRecipient(
			DuplicateEmailRecipientException exception, HttpServletRequest request) {
		return response(HttpStatus.CONFLICT, "DUPLICATE_EMAIL_RECIPIENT",
				exception, request);
	}

	@ExceptionHandler(InvalidEmailShareRequestException.class)
	public ResponseEntity<ApiError> handleInvalidRequest(
			InvalidEmailShareRequestException exception, HttpServletRequest request) {
		return response(HttpStatus.BAD_REQUEST, "INVALID_EMAIL_REQUEST",
				exception, request);
	}

	private ResponseEntity<ApiError> response(
			HttpStatus status, String code, RuntimeException exception,
			HttpServletRequest request) {
		return ResponseEntity.status(status).body(ApiError.of(
				status.value(), code, exception.getMessage(), request.getRequestURI()));
	}
}
