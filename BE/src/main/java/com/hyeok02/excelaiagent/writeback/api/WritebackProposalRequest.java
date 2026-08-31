package com.hyeok02.excelaiagent.writeback.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record WritebackProposalRequest(
		@NotBlank @Size(min = 2, max = 1000) String instruction) {}
