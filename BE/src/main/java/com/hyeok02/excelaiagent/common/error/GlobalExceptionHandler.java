package com.hyeok02.excelaiagent.common.error;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import com.hyeok02.excelaiagent.analysis.error.AnalysisFileStorageException;
import com.hyeok02.excelaiagent.analysis.error.InvalidExcelFileException;
import jakarta.servlet.http.HttpServletRequest;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

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

	@ExceptionHandler(InvalidExcelFileException.class)
	public ResponseEntity<ApiError> handleInvalidExcelFile(
			InvalidExcelFileException exception,
			HttpServletRequest request) {
		ApiError body = ApiError.of(
				HttpStatus.BAD_REQUEST.value(),
				"INVALID_EXCEL_FILE",
				exception.getMessage(),
				request.getRequestURI());

		return ResponseEntity.badRequest().body(body);
	}

	@ExceptionHandler(MethodArgumentTypeMismatchException.class)
	public ResponseEntity<ApiError> handleTypeMismatch(
			MethodArgumentTypeMismatchException exception,
			HttpServletRequest request) {
		String message = "mode는 BFS 또는 LLM 중 하나여야 합니다.";
		ApiError body = ApiError.of(
				HttpStatus.BAD_REQUEST.value(),
				"INVALID_ANALYSIS_MODE",
				message,
				request.getRequestURI());

		return ResponseEntity.badRequest().body(body);
	}

	@ExceptionHandler({MissingServletRequestPartException.class, MissingServletRequestParameterException.class})
	public ResponseEntity<ApiError> handleMissingRequestValue(
			Exception exception,
			HttpServletRequest request) {
		ApiError body = ApiError.of(
				HttpStatus.BAD_REQUEST.value(),
				"MISSING_REQUEST_VALUE",
				"file과 mode는 필수 입력값입니다.",
				request.getRequestURI());

		return ResponseEntity.badRequest().body(body);
	}

	@ExceptionHandler(AnalysisFileStorageException.class)
	public ResponseEntity<ApiError> handleFileStorage(
			AnalysisFileStorageException exception,
			HttpServletRequest request) {
		ApiError body = ApiError.of(
				HttpStatus.INTERNAL_SERVER_ERROR.value(),
				"FILE_STORAGE_ERROR",
				"업로드 파일을 저장하지 못했습니다.",
				request.getRequestURI());

		return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(body);
	}
}
