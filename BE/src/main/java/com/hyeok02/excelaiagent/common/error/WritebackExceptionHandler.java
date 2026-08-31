package com.hyeok02.excelaiagent.common.error;

import com.hyeok02.excelaiagent.writeback.error.InvalidWritebackStateException;
import com.hyeok02.excelaiagent.writeback.error.WritebackNotFoundException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class WritebackExceptionHandler {
	@ExceptionHandler(WritebackNotFoundException.class)
	public ResponseEntity<ApiError> notFound(
			WritebackNotFoundException exception, HttpServletRequest request) {
		return error(HttpStatus.NOT_FOUND, "WRITEBACK_NOT_FOUND", exception, request);
	}

	@ExceptionHandler(InvalidWritebackStateException.class)
	public ResponseEntity<ApiError> invalidState(
			InvalidWritebackStateException exception, HttpServletRequest request) {
		return error(HttpStatus.CONFLICT, "INVALID_WRITEBACK_STATE", exception, request);
	}

	private ResponseEntity<ApiError> error(
			HttpStatus status, String code, RuntimeException exception,
			HttpServletRequest request) {
		return ResponseEntity.status(status).body(ApiError.of(
				status.value(), code, exception.getMessage(), request.getRequestURI()));
	}
}
