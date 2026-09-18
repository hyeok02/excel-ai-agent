package com.hyeok02.excelaiagent.writeback.api;

import java.util.List;

/**
 * 승인 요청. approvedCells가 비어 있으면 제안한 변경 전체를 승인한 것으로 본다.
 */
public record WritebackApprovalRequest(boolean confirmed, List<String> approvedCells) {
	public List<String> approvedCells() {
		return approvedCells == null ? List.of() : approvedCells;
	}
}
