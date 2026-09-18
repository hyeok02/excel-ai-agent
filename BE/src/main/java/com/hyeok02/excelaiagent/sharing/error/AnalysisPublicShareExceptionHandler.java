package com.hyeok02.excelaiagent.sharing.error;

import java.time.Instant;
import java.util.Map;

import com.hyeok02.excelaiagent.common.error.ApiError;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class AnalysisPublicShareExceptionHandler {

	@ExceptionHandler(AnalysisPublicShareNotFoundException.class)
	public ResponseEntity<ApiError> handleNotFound(
			AnalysisPublicShareNotFoundException exception) {
		ApiError body = new ApiError(
				Instant.now(), HttpStatus.NOT_FOUND.value(), "ANALYSIS_SHARE_NOT_FOUND",
				exception.getMessage(), "/api/v1/public/analysis-shares/{token}", Map.of());
		return ResponseEntity.status(HttpStatus.NOT_FOUND).body(body);
	}
}
