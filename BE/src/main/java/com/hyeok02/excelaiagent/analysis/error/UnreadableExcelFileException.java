package com.hyeok02.excelaiagent.analysis.error;

/** Only fixed, user-safe messages may be persisted for an upstream file rejection. */
public class UnreadableExcelFileException extends InvalidExcelFileException {

	public static final String STYLE_MESSAGE =
			"Excel 서식 정보를 읽을 수 없습니다. 파일을 Excel에서 다시 저장한 뒤 업로드해 주세요.";
	public static final String INVALID_FORMAT_MESSAGE = "올바른 Excel 파일이 아닙니다.";
	public static final String DATA_MODEL_MESSAGE =
			"Power Pivot 내부 데이터 모델이 있지만 선택한 워크시트에서는 분석할 셀 표를 확인하지 못했습니다. "
			+ "안내 문구를 업무 데이터로 대신 분석하지 않았습니다. "
			+ "Excel에서 내부 모델의 데이터를 워크시트 표로 내보낸 뒤 .xlsx로 저장해 주세요. "
			+ "숨김 시트에 셀 표가 있다면 숨김 시트 포함 옵션으로 다시 시도할 수 있습니다.";
	public static final String LEGACY_XLS_MESSAGE =
			"구형 .xls 파일은 직접 분석하지 않습니다. "
			+ "Excel에서 '다른 이름으로 저장'으로 .xlsx 형식으로 변환해 주세요. "
			+ "파일 이름의 확장자만 바꾸면 변환되지 않습니다.";

	public UnreadableExcelFileException() {
		this(STYLE_MESSAGE);
	}

	private UnreadableExcelFileException(String message) {
		super(message);
	}

	public static UnreadableExcelFileException invalidFormat() {
		return new UnreadableExcelFileException(INVALID_FORMAT_MESSAGE);
	}

	public static UnreadableExcelFileException dataModelOnly() {
		return new UnreadableExcelFileException(DATA_MODEL_MESSAGE);
	}

	public static UnreadableExcelFileException legacyXls() {
		return new UnreadableExcelFileException(LEGACY_XLS_MESSAGE);
	}
}
