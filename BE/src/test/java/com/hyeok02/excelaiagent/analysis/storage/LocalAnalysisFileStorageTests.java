package com.hyeok02.excelaiagent.analysis.storage;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;

class LocalAnalysisFileStorageTests {

	@TempDir
	private Path uploadRoot;

	@Test
	void deletesStoredAnalysisDirectory() {
		LocalAnalysisFileStorage storage = createStorage();
		UUID analysisId = UUID.randomUUID();
		MockMultipartFile file = new MockMultipartFile("file", "sales.xlsx", null, new byte[] {1, 2, 3});

		storage.store(analysisId, "xlsx", file);
		Path analysisDirectory = uploadRoot.resolve(analysisId.toString());
		assertThat(Files.exists(analysisDirectory.resolve("source.xlsx"))).isTrue();

		storage.delete(analysisId);

		assertThat(Files.notExists(analysisDirectory)).isTrue();
	}

	@Test
	void ignoresMissingAnalysisDirectory() {
		LocalAnalysisFileStorage storage = createStorage();

		storage.delete(UUID.randomUUID());
	}

	private LocalAnalysisFileStorage createStorage() {
		AppProperties properties = new AppProperties(
				null,
				null,
				null,
				new AppProperties.Storage(uploadRoot.toString()));
		return new LocalAnalysisFileStorage(properties);
	}
}
