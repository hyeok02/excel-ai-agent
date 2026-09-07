package com.hyeok02.excelaiagent.analysis.storage;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
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
	private final LocalAnalysisDirectoryCleaner directoryCleaner;

	public LocalAnalysisFileStorage(AppProperties appProperties) {
		this.uploadRoot = Path.of(appProperties.storage().uploadDir()).toAbsolutePath().normalize();
		this.directoryCleaner = new LocalAnalysisDirectoryCleaner(uploadRoot);
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
		directoryCleaner.delete(resolveAnalysisDirectory(analysisId));
	}

	@Override
	public int deleteOlderThan(Instant cutoff) {
		return directoryCleaner.deleteOlderThan(cutoff);
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

}
