package com.hyeok02.excelaiagent.common.error;

import com.hyeok02.excelaiagent.analysis.error.AnalysisFileStorageException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisNotFoundException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultNotReadyException;
import com.hyeok02.excelaiagent.analysis.error.AnalysisResultPersistenceException;
import com.hyeok02.excelaiagent.analysis.error.InvalidExcelFileException;
import com.hyeok02.excelaiagent.integration.ai.AiServiceUnavailableException;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class AnalysisExceptionHandler {
	@ExceptionHandler(InvalidExcelFileException.class)
	public ResponseEntity<ApiError> handleInvalidExcelFile(
			InvalidExcelFileException exception, HttpServletRequest request) {
		return error(HttpStatus.BAD_REQUEST, "INVALID_EXCEL_FILE", exception.getMessage(), request);
	}

	@ExceptionHandler(AnalysisFileStorageException.class)
	public ResponseEntity<ApiError> handleFileStorage(
			AnalysisFileStorageException exception, HttpServletRequest request) {
		return error(HttpStatus.INTERNAL_SERVER_ERROR, "FILE_STORAGE_ERROR", exception.getMessage(), request);
	}

	@ExceptionHandler(AnalysisNotFoundException.class)
	public ResponseEntity<ApiError> handleAnalysisNotFound(
			AnalysisNotFoundException exception, HttpServletRequest request) {
		return error(HttpStatus.NOT_FOUND, "ANALYSIS_NOT_FOUND", exception.getMessage(), request);
	}

	@ExceptionHandler(AiServiceUnavailableException.class)
	public ResponseEntity<ApiError> handleAiServiceUnavailable(
			AiServiceUnavailableException exception, HttpServletRequest request) {
		return error(HttpStatus.SERVICE_UNAVAILABLE, "AI_SERVICE_UNAVAILABLE",
				"AI Service에 연결할 수 없습니다.", request);
	}

	@ExceptionHandler(AnalysisResultNotReadyException.class)
	public ResponseEntity<ApiError> handleAnalysisResultNotReady(
			AnalysisResultNotReadyException exception, HttpServletRequest request) {
		return error(HttpStatus.CONFLICT, "ANALYSIS_RESULT_NOT_READY", exception.getMessage(), request);
	}

	@ExceptionHandler(AnalysisResultPersistenceException.class)
	public ResponseEntity<ApiError> handleAnalysisResultPersistence(
			AnalysisResultPersistenceException exception, HttpServletRequest request) {
		return error(HttpStatus.INTERNAL_SERVER_ERROR,
				"ANALYSIS_RESULT_ERROR", exception.getMessage(), request);
	}

	private ResponseEntity<ApiError> error(
			HttpStatus status, String code, String message, HttpServletRequest request) {
		return ResponseEntity.status(status).body(ApiError.of(
				status.value(), code, message, request.getRequestURI()));
	}
}
