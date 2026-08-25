package com.hyeok02.excelaiagent.integration.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.List;

import org.junit.jupiter.api.Test;

class SheetClassificationTests {

	@Test
	void exposesStableRoleAndImportanceWireValues() {
		assertThat(SheetRole.values())
				.extracting(SheetRole::value)
				.containsExactly("input", "calculation", "output", "documentation", "system");
		assertThat(SheetImportance.values())
				.extracting(SheetImportance::value)
				.containsExactly("low", "medium", "high", "critical");
	}

	@Test
	void parsesKnownWireValues() {
		assertThat(SheetRole.fromValue("calculation")).isEqualTo(SheetRole.CALCULATION);
		assertThat(SheetImportance.fromValue("critical")).isEqualTo(SheetImportance.CRITICAL);
	}

	@Test
	void rejectsUnknownWireValues() {
		assertThatThrownBy(() -> SheetRole.fromValue("unknown"))
				.isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> SheetImportance.fromValue("urgent"))
				.isInstanceOf(IllegalArgumentException.class);
	}

	@Test
	void validatesClassificationRanges() {
		assertThatThrownBy(() -> new AiSheetClassification(
				SheetRole.OUTPUT,
				SheetImportance.HIGH,
				1.1,
				60,
				List.of()))
				.isInstanceOf(IllegalArgumentException.class);
		assertThatThrownBy(() -> new AiSheetClassification(
				SheetRole.OUTPUT,
				SheetImportance.HIGH,
				0.9,
				101,
				List.of()))
				.isInstanceOf(IllegalArgumentException.class);
	}
}
