package com.hyeok02.excelaiagent.analysis.storage;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.error.AnalysisFileStorageException;
import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

@Component
public class LocalAnalysisFileStorage implements AnalysisFileStorage {

	private final Path uploadRoot;

	public LocalAnalysisFileStorage(AppProperties appProperties) {
		this.uploadRoot = Path.of(appProperties.storage().uploadDir()).toAbsolutePath().normalize();
	}

	@Override
	public void store(UUID analysisId, String extension, MultipartFile file) {
		Path analysisDirectory = uploadRoot.resolve(analysisId.toString()).normalize();
		Path target = analysisDirectory.resolve("source." + extension).normalize();

		if (!target.startsWith(uploadRoot)) {
			throw new AnalysisFileStorageException("안전하지 않은 저장 경로입니다.", null);
		}

		try {
			Files.createDirectories(analysisDirectory);
			try (InputStream inputStream = file.getInputStream()) {
				Files.copy(inputStream, target, StandardCopyOption.REPLACE_EXISTING);
			}
		}
		catch (IOException exception) {
			throw new AnalysisFileStorageException("업로드 파일을 저장하지 못했습니다.", exception);
		}
	}
}
