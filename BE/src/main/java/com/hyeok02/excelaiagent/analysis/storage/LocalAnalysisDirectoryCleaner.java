package com.hyeok02.excelaiagent.analysis.storage;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Comparator;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.error.AnalysisFileStorageException;

final class LocalAnalysisDirectoryCleaner {
	private final Path uploadRoot;

	LocalAnalysisDirectoryCleaner(Path uploadRoot) {
		this.uploadRoot = uploadRoot;
	}

	int deleteOlderThan(Instant cutoff) {
		if (Files.notExists(uploadRoot)) {
			return 0;
		}

		int deletedCount = 0;
		try (var paths = Files.list(uploadRoot)) {
			for (Path path : paths.toList()) {
				if (!isAnalysisDirectory(path)) {
					continue;
				}
				Instant lastModifiedAt = Files.getLastModifiedTime(path, LinkOption.NOFOLLOW_LINKS).toInstant();
				if (lastModifiedAt.isBefore(cutoff)) {
					delete(path);
					deletedCount++;
				}
			}
			return deletedCount;
		}
		catch (IOException exception) {
			throw new AnalysisFileStorageException("만료된 업로드 파일을 정리하지 못했습니다.", exception);
		}
	}

	void delete(Path analysisDirectory) {
		if (!analysisDirectory.startsWith(uploadRoot)) {
			throw new AnalysisFileStorageException("안전하지 않은 삭제 경로입니다.", null);
		}
		if (Files.notExists(analysisDirectory)) {
			return;
		}

		try (var paths = Files.walk(analysisDirectory)) {
			for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) {
				Files.deleteIfExists(path);
			}
		}
		catch (IOException exception) {
			throw new AnalysisFileStorageException("업로드 파일을 삭제하지 못했습니다.", exception);
		}
	}

	private boolean isAnalysisDirectory(Path path) {
		if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)) {
			return false;
		}
		try {
			UUID.fromString(path.getFileName().toString());
			return true;
		}
		catch (IllegalArgumentException exception) {
			return false;
		}
	}
}
