package com.hyeok02.excelaiagent.analysis.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record WorkbookQuestionRequest(
		@NotBlank(message = "질문을 입력해주세요.")
		@Size(min = 2, max = 1000, message = "질문은 2자 이상 1000자 이하로 입력해주세요.")
		String question) {
}
