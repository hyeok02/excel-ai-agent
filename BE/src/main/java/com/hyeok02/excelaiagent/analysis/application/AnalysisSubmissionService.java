package com.hyeok02.excelaiagent.analysis.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.domain.AnalysisMode;
import com.hyeok02.excelaiagent.analysis.domain.AnalysisStatus;
import com.hyeok02.excelaiagent.analysis.storage.AnalysisFileStorage;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class AnalysisSubmissionService {

	private final ExcelFileValidator excelFileValidator;
	private final AnalysisFileStorage analysisFileStorage;

	public AnalysisSubmissionService(
			ExcelFileValidator excelFileValidator,
			AnalysisFileStorage analysisFileStorage) {
		this.excelFileValidator = excelFileValidator;
		this.analysisFileStorage = analysisFileStorage;
	}

	public AnalysisSubmission submit(MultipartFile file, AnalysisMode mode) {
		ValidatedExcelFile validatedFile = excelFileValidator.validate(file);
		UUID analysisId = UUID.randomUUID();

		analysisFileStorage.store(analysisId, validatedFile.extension(), file);

		return new AnalysisSubmission(
				analysisId,
				AnalysisStatus.QUEUED,
				mode,
				validatedFile.originalFilename(),
				validatedFile.sizeBytes(),
				Instant.now());
	}
}
