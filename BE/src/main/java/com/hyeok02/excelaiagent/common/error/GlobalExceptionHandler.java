package com.hyeok02.excelaiagent.common.error;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

@RestControllerAdvice
public class GlobalExceptionHandler {

	@ExceptionHandler(MethodArgumentNotValidException.class)
	public ResponseEntity<ApiError> handleValidation(
			MethodArgumentNotValidException exception,
			HttpServletRequest request) {
		Map<String, String> fieldErrors = new LinkedHashMap<>();
		exception.getBindingResult().getFieldErrors().forEach(error ->
				fieldErrors.putIfAbsent(error.getField(), error.getDefaultMessage()));

		ApiError body = new ApiError(
				Instant.now(),
				HttpStatus.BAD_REQUEST.value(),
				"VALIDATION_ERROR",
				"요청 값을 확인해주세요.",
				request.getRequestURI(),
				Map.copyOf(fieldErrors));

		return ResponseEntity.badRequest().body(body);
	}

	@ExceptionHandler(MaxUploadSizeExceededException.class)
	public ResponseEntity<ApiError> handleMaxUploadSize(
			MaxUploadSizeExceededException exception,
			HttpServletRequest request) {
		ApiError body = ApiError.of(
				HttpStatus.CONTENT_TOO_LARGE.value(),
				"FILE_TOO_LARGE",
				"업로드 파일은 50MB를 초과할 수 없습니다.",
				request.getRequestURI());

		return ResponseEntity.status(HttpStatus.CONTENT_TOO_LARGE).body(body);
	}
}
