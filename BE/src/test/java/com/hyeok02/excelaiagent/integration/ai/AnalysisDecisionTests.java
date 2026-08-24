package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class AnalysisDecisionTests {

	@Test
	void convertsWireValues() {
		assertThat(AnalysisDecision.fromValue("include")).isEqualTo(AnalysisDecision.INCLUDE);
		assertThat(AnalysisDecision.EXCLUDE.value()).isEqualTo("exclude");
	}

	@Test
	void rejectsUnknownWireValue() {
		assertThatThrownBy(() -> AnalysisDecision.fromValue("skip"))
				.isInstanceOf(IllegalArgumentException.class);
	}
}
