package com.hyeok02.excelaiagent.writeback.application;

import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Collectors;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import com.hyeok02.excelaiagent.writeback.error.InvalidWritebackStateException;

/**
 * 승인한 셀만 골라 적용 대상을 좁힌다. 셀 주소는 대소문자를 구분하지 않고,
 * 시트 이름은 Excel과 같게 그대로 비교한다.
 */
final class WritebackApprovalScope {
	private WritebackApprovalScope() {}

	static List<AiWritebackProposal.Change> select(
			List<AiWritebackProposal.Change> changes, List<String> approvedCells) {
		if (approvedCells.isEmpty()) {
			return changes;
		}
		Set<String> approved = approvedCells.stream()
				.map(WritebackApprovalScope::normalize)
				.collect(Collectors.toSet());
		List<AiWritebackProposal.Change> selected = changes.stream()
				.filter(change -> approved.contains(key(change.sheetName(), change.reference())))
				.toList();
		if (selected.size() != approved.size()) {
			throw new InvalidWritebackStateException("승인 목록에 제안에 없는 셀이 포함되어 있습니다.");
		}
		return selected;
	}

	private static String normalize(String cell) {
		int separator = cell.lastIndexOf('!');
		if (separator < 0) {
			throw new InvalidWritebackStateException("승인할 셀은 시트 이름과 함께 지정해야 합니다.");
		}
		return key(cell.substring(0, separator), cell.substring(separator + 1));
	}

	private static String key(String sheetName, String reference) {
		return sheetName.trim() + '!' + reference.trim().toUpperCase(Locale.ROOT);
	}
}
