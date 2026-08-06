package com.hyeok02.excelaiagent.analysis.storage;

import java.util.UUID;

import org.springframework.web.multipart.MultipartFile;

public interface AnalysisFileStorage {

	void store(UUID analysisId, String extension, MultipartFile file);
}
