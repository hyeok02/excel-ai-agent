package com.hyeok02.excelaiagent.analysis.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.hyeok02.excelaiagent.analysis.error.InvalidExcelFileException;
import com.hyeok02.excelaiagent.common.config.AppProperties;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.util.unit.DataSize;

class ExcelFileValidatorTests {

	private static final byte[] ZIP_FILE = {0x50, 0x4b, 0x03, 0x04, 0x01};

	private final ExcelFileValidator validator = new ExcelFileValidator(new AppProperties(
			null,
			null,
			new AppProperties.Analysis(DataSize.ofMegabytes(50)),
			null));

	@Test
	void acceptsXlsxFileWithZipSignature() {
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"sales.xlsx",
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				ZIP_FILE);

		ValidatedExcelFile result = validator.validate(file);

		assertThat(result.originalFilename()).isEqualTo("sales.xlsx");
		assertThat(result.extension()).isEqualTo("xlsx");
		assertThat(result.sizeBytes()).isEqualTo(ZIP_FILE.length);
	}

	@Test
	void rejectsEmptyFile() {
		MockMultipartFile file = new MockMultipartFile("file", "sales.xlsx", null, new byte[0]);

		assertThatThrownBy(() -> validator.validate(file))
				.isInstanceOf(InvalidExcelFileException.class)
				.hasMessage("비어 있는 파일은 업로드할 수 없습니다.");
	}

	@Test
	void rejectsUnsupportedExtension() {
		MockMultipartFile file = new MockMultipartFile("file", "sales.xls", null, ZIP_FILE);

		assertThatThrownBy(() -> validator.validate(file))
				.isInstanceOf(InvalidExcelFileException.class)
				.hasMessage(".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다.");
	}

	@Test
	void rejectsFileWhoseContentIsNotAnExcelZip() {
		MockMultipartFile file = new MockMultipartFile(
				"file",
				"renamed.xlsx",
				null,
				"not an excel file".getBytes());

		assertThatThrownBy(() -> validator.validate(file))
				.isInstanceOf(InvalidExcelFileException.class)
				.hasMessage("Excel 파일의 내용이 올바르지 않습니다.");
	}
}
