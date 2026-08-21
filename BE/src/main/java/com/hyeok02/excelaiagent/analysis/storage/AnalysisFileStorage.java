package com.hyeok02.excelaiagent.analysis.storage;

import java.time.Instant;
import java.util.UUID;

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

public interface AnalysisFileStorage {

	void store(UUID analysisId, String extension, MultipartFile file);

	Resource load(UUID analysisId, String extension);

	void delete(UUID analysisId);

	int deleteOlderThan(Instant cutoff);
}
