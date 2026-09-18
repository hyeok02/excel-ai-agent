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

	@ExceptionHandler(TelegramRecipientNotFoundException.class)
	public ResponseEntity<ApiError> handleRecipientNotFound(
			TelegramRecipientNotFoundException exception, HttpServletRequest request) {
		return response(HttpStatus.NOT_FOUND, "TELEGRAM_RECIPIENT_NOT_FOUND",
				exception.getMessage(), request);
	}

	@ExceptionHandler(TelegramInvitationNotFoundException.class)
	public ResponseEntity<ApiError> handleInvitationNotFound(
			TelegramInvitationNotFoundException exception, HttpServletRequest request) {
		return response(HttpStatus.NOT_FOUND, "TELEGRAM_INVITATION_NOT_FOUND",
				exception.getMessage(), request);
	}

	@ExceptionHandler({InvalidTelegramInvitationException.class,
			InvalidTelegramShareRequestException.class})
	public ResponseEntity<ApiError> handleInvalidRequest(
			RuntimeException exception, HttpServletRequest request) {
		return response(HttpStatus.BAD_REQUEST, "INVALID_TELEGRAM_REQUEST",
				exception.getMessage(), request);
	}

	@ExceptionHandler(TelegramWebhookUnauthorizedException.class)
	public ResponseEntity<ApiError> handleUnauthorizedWebhook(
			TelegramWebhookUnauthorizedException exception, HttpServletRequest request) {
		return response(HttpStatus.UNAUTHORIZED, "INVALID_TELEGRAM_WEBHOOK_SECRET",
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
