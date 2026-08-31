package com.hyeok02.excelaiagent.writeback.error;

import java.util.UUID;

public class WritebackNotFoundException extends RuntimeException {
	public WritebackNotFoundException(UUID writebackId) {
		super("Excel 변경 작업을 찾을 수 없습니다: " + writebackId);
	}
}
