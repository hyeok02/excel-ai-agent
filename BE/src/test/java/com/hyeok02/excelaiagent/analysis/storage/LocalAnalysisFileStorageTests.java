package com.hyeok02.excelaiagent.analysis.storage;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.time.Duration;
import java.time.Instant;
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

	@Test
	void loadsStoredAnalysisFile() throws Exception {
		LocalAnalysisFileStorage storage = createStorage();
		UUID analysisId = UUID.randomUUID();
		storage.store(analysisId, "xlsx", new MockMultipartFile(
				"file", "sales.xlsx", null, new byte[] {1, 2, 3}));

		assertThat(storage.load(analysisId, "xlsx").getContentAsByteArray())
				.containsExactly(1, 2, 3);
	}

	@Test
	void deletesOnlyExpiredAnalysisDirectories() throws Exception {
		LocalAnalysisFileStorage storage = createStorage();
		UUID expiredId = UUID.randomUUID();
		UUID recentId = UUID.randomUUID();
		storage.store(expiredId, "xlsx", new MockMultipartFile("file", "old.xlsx", null, new byte[] {1}));
		storage.store(recentId, "xlsx", new MockMultipartFile("file", "new.xlsx", null, new byte[] {2}));
		Files.setLastModifiedTime(
				uploadRoot.resolve(expiredId.toString()),
				FileTime.from(Instant.now().minus(Duration.ofDays(2))));

		int deletedCount = storage.deleteOlderThan(Instant.now().minus(Duration.ofDays(1)));

		assertThat(deletedCount).isEqualTo(1);
		assertThat(Files.notExists(uploadRoot.resolve(expiredId.toString()))).isTrue();
		assertThat(Files.exists(uploadRoot.resolve(recentId.toString()))).isTrue();
	}

	private LocalAnalysisFileStorage createStorage() {
		AppProperties properties = new AppProperties(
				null,
				null,
				null,
				new AppProperties.Storage(uploadRoot.toString(), Duration.ofDays(1)));
		return new LocalAnalysisFileStorage(properties);
	}
}
