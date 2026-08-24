package com.hyeok02.excelaiagent.integration.ai;

import java.util.Arrays;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum AnalysisDecision {

	INCLUDE("include"),
	EXCLUDE("exclude");

	private final String value;

	AnalysisDecision(String value) {
		this.value = value;
	}

	@JsonValue
	public String value() {
		return value;
	}

	@JsonCreator
	public static AnalysisDecision fromValue(String value) {
		return Arrays.stream(values())
				.filter(decision -> decision.value.equals(value))
				.findFirst()
				.orElseThrow(() -> new IllegalArgumentException("알 수 없는 분석 포함 결정입니다: " + value));
	}
}
