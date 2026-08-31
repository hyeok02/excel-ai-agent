package com.hyeok02.excelaiagent.writeback.application;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackManifest;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

final class WritebackJson {
	private final ObjectMapper objectMapper;

	WritebackJson(ObjectMapper objectMapper) {
		this.objectMapper = objectMapper;
	}

	String proposal(AiWritebackProposal proposal) {
		return write(proposal);
	}

	String manifest(AiWritebackManifest manifest) {
		return write(manifest);
	}

	AiWritebackProposal proposal(String value) {
		try {
			return objectMapper.readValue(value, AiWritebackProposal.class);
		}
		catch (JacksonException exception) {
			throw new IllegalStateException("저장된 변경 제안을 읽을 수 없습니다.", exception);
		}
	}

	AiWritebackManifest manifestOrNull(String value) {
		if (value == null) return null;
		try {
			return objectMapper.readValue(value, AiWritebackManifest.class);
		}
		catch (JacksonException exception) {
			throw new IllegalStateException("저장된 검증 결과를 읽을 수 없습니다.", exception);
		}
	}

	private String write(Object value) {
		try {
			return objectMapper.writeValueAsString(value);
		}
		catch (JacksonException exception) {
			throw new IllegalStateException("변경 정보를 저장할 수 없습니다.", exception);
		}
	}
}
