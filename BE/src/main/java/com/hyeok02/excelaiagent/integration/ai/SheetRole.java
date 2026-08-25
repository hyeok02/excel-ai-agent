package com.hyeok02.excelaiagent.integration.ai;

import java.util.Arrays;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum SheetRole {

	INPUT("input"),
	CALCULATION("calculation"),
	OUTPUT("output"),
	DOCUMENTATION("documentation"),
	SYSTEM("system");

	private final String value;

	SheetRole(String value) {
		this.value = value;
	}

	@JsonValue
	public String value() {
		return value;
	}

	@JsonCreator
	public static SheetRole fromValue(String value) {
		return Arrays.stream(values())
				.filter(role -> role.value.equals(value))
				.findFirst()
				.orElseThrow(() -> new IllegalArgumentException("알 수 없는 시트 역할입니다: " + value));
	}
}
