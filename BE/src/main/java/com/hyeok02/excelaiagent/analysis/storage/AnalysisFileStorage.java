package com.hyeok02.excelaiagent.analysis.storage;

import java.time.Instant;
import java.util.UUID;

import org.springframework.core.io.Resource;
import org.springframework.web.multipart.MultipartFile;

public interface AnalysisFileStorage {

	void store(UUID analysisId, String extension, MultipartFile file);

	Resource load(UUID analysisId, String extension);

	boolean exists(UUID analysisId, String extension);

	void storeWriteback(UUID analysisId, UUID writebackId, String extension, byte[] content);

	Resource loadWriteback(UUID analysisId, UUID writebackId, String extension);

	void delete(UUID analysisId);

	int deleteOlderThan(Instant cutoff);
}
