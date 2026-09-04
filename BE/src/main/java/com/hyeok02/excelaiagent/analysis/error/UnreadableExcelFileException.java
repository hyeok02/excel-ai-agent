package com.hyeok02.excelaiagent.analysis.error;

/** Only fixed, user-safe messages may be persisted for an upstream file rejection. */
public class UnreadableExcelFileException extends InvalidExcelFileException {

	public static final String STYLE_MESSAGE =
			"Excel 서식 정보를 읽을 수 없습니다. 파일을 Excel에서 다시 저장한 뒤 업로드해 주세요.";
	public static final String INVALID_FORMAT_MESSAGE = "올바른 Excel 파일이 아닙니다.";

	public UnreadableExcelFileException() {
		this(STYLE_MESSAGE);
	}

	private UnreadableExcelFileException(String message) {
		super(message);
	}

	public static UnreadableExcelFileException invalidFormat() {
		return new UnreadableExcelFileException(INVALID_FORMAT_MESSAGE);
	}
}
