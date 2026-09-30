package com.hyeok02.excelaiagent.common.error;

import com.hyeok02.excelaiagent.auth.error.DuplicateUsernameException;
import com.hyeok02.excelaiagent.auth.error.InvalidCredentialsException;
import com.hyeok02.excelaiagent.auth.error.LastActiveAdminException;
import com.hyeok02.excelaiagent.auth.error.SelfDeactivationException;
import com.hyeok02.excelaiagent.auth.error.SsoAccessDeniedException;
import com.hyeok02.excelaiagent.auth.error.UserAccountNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class AuthExceptionHandler {
	@ExceptionHandler(InvalidCredentialsException.class)
	public ResponseEntity<ApiError> handleInvalidCredentials(
			InvalidCredentialsException exception, HttpServletRequest request) {
		return error(HttpStatus.UNAUTHORIZED, "INVALID_CREDENTIALS", exception, request);
	}

	@ExceptionHandler(DuplicateUsernameException.class)
	public ResponseEntity<ApiError> handleDuplicateUsername(
			DuplicateUsernameException exception, HttpServletRequest request) {
		return error(HttpStatus.CONFLICT, "DUPLICATE_USERNAME", exception, request);
	}

	@ExceptionHandler(SsoAccessDeniedException.class)
	public ResponseEntity<ApiError> handleSsoAccessDenied(
			SsoAccessDeniedException exception, HttpServletRequest request) {
		return error(HttpStatus.FORBIDDEN, "SSO_ACCESS_DENIED", exception, request);
	}

	@ExceptionHandler(UserAccountNotFoundException.class)
	public ResponseEntity<ApiError> handleUserNotFound(
			UserAccountNotFoundException exception, HttpServletRequest request) {
		return error(HttpStatus.NOT_FOUND, "USER_NOT_FOUND", exception, request);
	}

	@ExceptionHandler(SelfDeactivationException.class)
	public ResponseEntity<ApiError> handleSelfDeactivation(
			SelfDeactivationException exception, HttpServletRequest request) {
		return error(HttpStatus.CONFLICT, "SELF_DEACTIVATION_NOT_ALLOWED", exception, request);
	}

	@ExceptionHandler(LastActiveAdminException.class)
	public ResponseEntity<ApiError> handleLastActiveAdmin(
			LastActiveAdminException exception, HttpServletRequest request) {
		return error(HttpStatus.CONFLICT, "LAST_ACTIVE_ADMIN_REQUIRED", exception, request);
	}

	private ResponseEntity<ApiError> error(
			HttpStatus status, String code, RuntimeException exception, HttpServletRequest request) {
		return ResponseEntity.status(status).body(ApiError.of(
				status.value(), code, exception.getMessage(), request.getRequestURI()));
	}
}
