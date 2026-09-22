package com.hyeok02.excelaiagent.writeback.application;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal.Change;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal.Change.RelatedCell;
import com.hyeok02.excelaiagent.writeback.error.InvalidWritebackStateException;

/**
 * 승인한 셀만 골라 적용 대상을 좁힌다. 셀 주소는 대소문자를 구분하지 않고,
 * 시트 이름은 Excel과 같게 그대로 비교한다. 변경안에 딸린 관련 셀도 함께 승인할 수
 * 있으며, 이때 그 관련 셀은 변경 한 건으로 펼쳐진다.
 */
final class WritebackApprovalScope {
	private WritebackApprovalScope() {}

	static List<Change> select(List<Change> changes, List<String> approvedCells) {
		if (approvedCells.isEmpty()) {
			return changes;
		}
		Set<String> approved = new LinkedHashSet<>();
		approvedCells.forEach(cell -> approved.add(normalize(cell)));
		List<Change> selected = new ArrayList<>();
		Set<String> taken = new LinkedHashSet<>();
		for (Change change : changes) {
			if (!approved.contains(key(change.sheetName(), change.reference()))) {
				continue;
			}
			add(selected, taken, change);
			for (RelatedCell related : change.relatedCells()) {
				if (approved.contains(key(related.sheetName(), related.reference()))) {
					add(selected, taken, asChange(related));
				}
			}
		}
		if (taken.size() != approved.size()) {
			throw new InvalidWritebackStateException("승인 목록에 제안에 없는 셀이 포함되어 있습니다.");
		}
		return selected;
	}

	private static void add(List<Change> selected, Set<String> taken, Change change) {
		if (taken.add(key(change.sheetName(), change.reference()))) {
			selected.add(change);
		}
	}

	private static Change asChange(RelatedCell related) {
		return new Change(
				related.sheetName(), related.reference(), related.suggestedValue(),
				related.reason(), related.currentValue(), List.of(),
				"value", "number", List.of(), "medium");
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
