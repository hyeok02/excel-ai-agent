package com.hyeok02.excelaiagent.analysis.application;

public record ValidatedExcelFile(
		String originalFilename,
		String extension,
		long sizeBytes) {
}
