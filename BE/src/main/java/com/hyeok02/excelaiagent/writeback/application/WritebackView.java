package com.hyeok02.excelaiagent.writeback.application;

import java.time.Instant;
import java.util.UUID;

import com.hyeok02.excelaiagent.integration.ai.AiWritebackManifest;
import com.hyeok02.excelaiagent.integration.ai.AiWritebackProposal;
import com.hyeok02.excelaiagent.writeback.domain.WorkbookWriteback;
import com.hyeok02.excelaiagent.writeback.domain.WritebackStatus;

public record WritebackView(
		UUID writebackId,
		UUID analysisId,
		WritebackStatus status,
		String instruction,
		AiWritebackProposal proposal,
		AiWritebackManifest verification,
		String requestedBy,
		String approvedBy,
		Instant createdAt,
		Instant updatedAt,
		boolean downloadable) {

	static WritebackView from(WorkbookWriteback item, WritebackJson json) {
		return new WritebackView(
				item.getWritebackId(), item.getAnalysisId(), item.getStatus(),
				item.getInstruction(), json.proposal(item.getProposalJson()),
				json.manifestOrNull(item.getVerificationJson()), item.getRequestedBy(),
				item.getApprovedBy(), item.getCreatedAt(), item.getUpdatedAt(),
				item.getStatus() == WritebackStatus.APPLIED);
	}
}
