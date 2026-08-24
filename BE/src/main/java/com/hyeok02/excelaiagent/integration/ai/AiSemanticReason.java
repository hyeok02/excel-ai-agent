package com.hyeok02.excelaiagent.integration.ai;

import java.util.HashSet;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

public record AiSemanticReason(
		String code,
		String message,
		@JsonProperty("evidence_cells") List<String> evidenceCells) {

	public AiSemanticReason {
		if (code == null || code.isBlank()) {
			throw new IllegalArgumentException("의미 역할 판단 근거 코드는 비어 있을 수 없습니다.");
		}
		if (message == null || message.isBlank()) {
			throw new IllegalArgumentException("의미 역할 판단 근거 설명은 비어 있을 수 없습니다.");
		}
		evidenceCells = evidenceCells == null ? List.of() : List.copyOf(evidenceCells);
		if (evidenceCells.stream().anyMatch(cell -> cell == null || cell.isBlank())) {
			throw new IllegalArgumentException("의미 역할 판단 근거 셀은 비어 있을 수 없습니다.");
		}
		if (evidenceCells.size() != new HashSet<>(evidenceCells).size()) {
			throw new IllegalArgumentException("의미 역할 판단 근거 셀은 중복될 수 없습니다.");
		}
	}
}
