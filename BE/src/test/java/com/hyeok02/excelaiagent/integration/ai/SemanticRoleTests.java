package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;

import org.junit.jupiter.api.Test;

class SemanticRoleTests {

	@Test
	void exposesStableWireValues() {
		assertThat(Arrays.stream(SemanticRole.values()).map(SemanticRole::value))
				.containsExactly(
						"title",
						"description",
						"unit",
						"header",
						"data",
						"formula",
						"note",
						"total",
						"input",
						"calculation",
						"output",
						"instruction",
						"warning",
						"source_note",
						"rule_note",
						"system_cache",
						"ignore",
						"unknown");
	}

	@Test
	void parsesKnownWireValue() {
		assertThat(SemanticRole.fromValue("source_note")).isEqualTo(SemanticRole.SOURCE_NOTE);
	}

	@Test
	void rejectsUnknownWireValue() {
		assertThatThrownBy(() -> SemanticRole.fromValue("other"))
				.isInstanceOf(IllegalArgumentException.class)
				.hasMessageContaining("other");
	}
}
