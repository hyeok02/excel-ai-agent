package com.hyeok02.excelaiagent.analysis.storage;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.Comparator;
import java.util.UUID;

import com.hyeok02.excelaiagent.analysis.error.AnalysisFileStorageException;
import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
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
	@Override
	public Resource load(UUID analysisId, String extension) {
		Path source = sourcePath(analysisId, extension);
		if (!source.startsWith(uploadRoot) || Files.notExists(source)) {
			throw new AnalysisFileStorageException("저장된 업로드 파일을 찾지 못했습니다.", null);
		}
		return new FileSystemResource(source);
	}

	@Override
	public boolean exists(UUID analysisId, String extension) {
		return Files.isRegularFile(sourcePath(analysisId, extension), LinkOption.NOFOLLOW_LINKS);
	}
	@Override
	public void storeWriteback(
			UUID analysisId, UUID writebackId, String extension, byte[] content) {
		Path directory = resolveAnalysisDirectory(analysisId)
				.resolve("writebacks").resolve(writebackId.toString()).normalize();
		Path target = directory.resolve("result." + extension).normalize();
		if (!target.startsWith(uploadRoot)) {
			throw new AnalysisFileStorageException("안전하지 않은 저장 경로입니다.", null);
		}
		try {
			Files.createDirectories(directory);
			Files.write(target, content);
		}
		catch (IOException exception) {
			throw new AnalysisFileStorageException("수정본을 저장하지 못했습니다.", exception);
		}
	}
	@Override
	public Resource loadWriteback(
			UUID analysisId, UUID writebackId, String extension) {
		Path target = resolveAnalysisDirectory(analysisId).resolve("writebacks")
				.resolve(writebackId.toString()).resolve("result." + extension).normalize();
		if (!target.startsWith(uploadRoot) || Files.notExists(target)) {
			throw new AnalysisFileStorageException("검증된 수정본을 찾지 못했습니다.", null);
		}
		return new FileSystemResource(target);
	}
	@Override
	public void delete(UUID analysisId) {
		deleteDirectory(resolveAnalysisDirectory(analysisId));
	}

	@Override
	public int deleteOlderThan(Instant cutoff) {
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
					deleteDirectory(path);
					deletedCount++;
				}
			}
			return deletedCount;
		}
		catch (IOException exception) {
			throw new AnalysisFileStorageException("만료된 업로드 파일을 정리하지 못했습니다.", exception);
		}
	}

	private Path resolveAnalysisDirectory(UUID analysisId) {
		Path analysisDirectory = uploadRoot.resolve(analysisId.toString()).normalize();
		if (!analysisDirectory.startsWith(uploadRoot)) {
			throw new AnalysisFileStorageException("안전하지 않은 저장 경로입니다.", null);
		}
		return analysisDirectory;
	}

	private Path sourcePath(UUID analysisId, String extension) {
		Path source = resolveAnalysisDirectory(analysisId).resolve("source." + extension).normalize();
		if (!source.startsWith(uploadRoot)) {
			throw new AnalysisFileStorageException("안전하지 않은 저장 경로입니다.", null);
		}
		return source;
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

	private void deleteDirectory(Path analysisDirectory) {
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
}
