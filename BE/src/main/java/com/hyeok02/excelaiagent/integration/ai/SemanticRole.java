package com.hyeok02.excelaiagent.integration.ai;

import java.util.Arrays;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum SemanticRole {

	TITLE("title"),
	DESCRIPTION("description"),
	UNIT("unit"),
	HEADER("header"),
	DATA("data"),
	FORMULA("formula"),
	NOTE("note"),
	TOTAL("total"),
	INPUT("input"),
	CALCULATION("calculation"),
	OUTPUT("output"),
	INSTRUCTION("instruction"),
	WARNING("warning"),
	SOURCE_NOTE("source_note"),
	RULE_NOTE("rule_note"),
	SYSTEM_CACHE("system_cache"),
	IGNORE("ignore"),
	UNKNOWN("unknown");

	private final String value;

	SemanticRole(String value) {
		this.value = value;
	}

	@JsonValue
	public String value() {
		return value;
	}

	@JsonCreator
	public static SemanticRole fromValue(String value) {
		return Arrays.stream(values())
				.filter(role -> role.value.equals(value))
				.findFirst()
				.orElseThrow(() -> new IllegalArgumentException("알 수 없는 의미 역할입니다: " + value));
	}
}
