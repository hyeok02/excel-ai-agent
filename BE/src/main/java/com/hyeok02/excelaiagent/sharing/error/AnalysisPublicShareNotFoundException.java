package com.hyeok02.excelaiagent.sharing.error;

public class AnalysisPublicShareNotFoundException extends RuntimeException {

	public AnalysisPublicShareNotFoundException() {
		super("공유 링크를 사용할 수 없습니다.");
	}
}
