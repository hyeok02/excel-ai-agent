package com.hyeok02.excelaiagent.integration.ai;

import java.util.Arrays;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum SheetImportance {

	LOW("low"),
	MEDIUM("medium"),
	HIGH("high"),
	CRITICAL("critical");

	private final String value;

	SheetImportance(String value) {
		this.value = value;
	}

	@JsonValue
	public String value() {
		return value;
	}

	@JsonCreator
	public static SheetImportance fromValue(String value) {
		return Arrays.stream(values())
				.filter(importance -> importance.value.equals(value))
				.findFirst()
				.orElseThrow(() -> new IllegalArgumentException("알 수 없는 시트 중요도입니다: " + value));
	}
}
