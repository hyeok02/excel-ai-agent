package com.hyeok02.excelaiagent.analysis.application;

import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.Set;

import com.hyeok02.excelaiagent.analysis.error.InvalidExcelFileException;
import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Component
public class ExcelFileValidator {

	private static final Set<String> SUPPORTED_EXTENSIONS = Set.of("xlsx", "xlsm");
	private static final byte[] ZIP_SIGNATURE = {0x50, 0x4b, 0x03, 0x04};

	private final long maxFileSizeBytes;

	public ExcelFileValidator(AppProperties appProperties) {
		this.maxFileSizeBytes = appProperties.analysis().maxFileSize().toBytes();
	}

	public ValidatedExcelFile validate(MultipartFile file) {
		if (file == null || file.isEmpty()) {
			throw new InvalidExcelFileException("비어 있는 파일은 업로드할 수 없습니다.");
		}

		if (file.getSize() > maxFileSizeBytes) {
			throw new InvalidExcelFileException("업로드 파일은 50MB를 초과할 수 없습니다.");
		}

		String originalFilename = StringUtils.cleanPath(
				file.getOriginalFilename() == null ? "" : file.getOriginalFilename());
		if (!StringUtils.hasText(originalFilename) || originalFilename.contains("..")) {
			throw new InvalidExcelFileException("파일 이름이 올바르지 않습니다.");
		}

		String extension = StringUtils.getFilenameExtension(originalFilename);
		if (extension == null || !SUPPORTED_EXTENSIONS.contains(extension.toLowerCase(Locale.ROOT))) {
			throw new InvalidExcelFileException(".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다.");
		}

		if (!hasZipSignature(file)) {
			throw new InvalidExcelFileException("Excel 파일의 내용이 올바르지 않습니다.");
		}

		return new ValidatedExcelFile(
				originalFilename,
				extension.toLowerCase(Locale.ROOT),
				file.getSize());
	}

	private boolean hasZipSignature(MultipartFile file) {
		try (InputStream inputStream = file.getInputStream()) {
			byte[] signature = inputStream.readNBytes(ZIP_SIGNATURE.length);
			return signature.length == ZIP_SIGNATURE.length
					&& signature[0] == ZIP_SIGNATURE[0]
					&& signature[1] == ZIP_SIGNATURE[1]
					&& signature[2] == ZIP_SIGNATURE[2]
					&& signature[3] == ZIP_SIGNATURE[3];
		}
		catch (IOException exception) {
			throw new InvalidExcelFileException("Excel 파일을 읽을 수 없습니다.");
		}
	}
}
