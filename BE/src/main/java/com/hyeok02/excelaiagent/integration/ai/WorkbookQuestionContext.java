package com.hyeok02.excelaiagent.integration.ai;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** Untrusted navigation hints only; answers and claimed facts are never forwarded. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record WorkbookQuestionContext(
		@Size(max = 6) List<@NotNull @Valid Turn> turns,
		@Size(max = 6) List<@NotNull @Valid Insight> insights) {

	public WorkbookQuestionContext {
		if (turns == null) turns = List.of();
		if (insights == null) insights = List.of();
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Turn(
			@NotBlank @Size(max = 1000) String question,
			@NotNull @Size(max = 12) List<@NotBlank @Size(max = 200) String> evidence) {
	}

	@JsonIgnoreProperties(ignoreUnknown = true)
	public record Insight(
			@NotBlank @Size(max = 200) String title,
			@Size(max = 200) String topic,
			@NotNull @Size(max = 12) List<@NotBlank @Size(max = 200) String> evidence) {
	}
}
