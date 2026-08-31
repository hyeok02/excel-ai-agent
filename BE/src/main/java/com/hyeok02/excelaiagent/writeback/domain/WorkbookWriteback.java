package com.hyeok02.excelaiagent.writeback.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "workbook_writebacks")
public class WorkbookWriteback {
	@Id @Column(name = "writeback_id", nullable = false, updatable = false)
	private UUID writebackId;
	@Column(name = "analysis_id", nullable = false, updatable = false)
	private UUID analysisId;
	@Enumerated(EnumType.STRING) @Column(name = "status", nullable = false, length = 20)
	private WritebackStatus status;
	@Column(name = "instruction", nullable = false, length = 1000)
	private String instruction;
	@Column(name = "proposal_json", nullable = false, columnDefinition = "CLOB")
	private String proposalJson;
	@Column(name = "verification_json", columnDefinition = "CLOB")
	private String verificationJson;
	@Column(name = "requested_by", nullable = false, length = 100)
	private String requestedBy;
	@Column(name = "approved_by", length = 100)
	private String approvedBy;
	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;
	@Column(name = "updated_at", nullable = false)
	private Instant updatedAt;

	protected WorkbookWriteback() {}

	public static WorkbookWriteback proposed(
			UUID analysisId, String instruction, String proposalJson,
			boolean blocked, String actor, Instant now) {
		WorkbookWriteback item = new WorkbookWriteback();
		item.writebackId = UUID.randomUUID();
		item.analysisId = analysisId;
		item.status = blocked ? WritebackStatus.BLOCKED : WritebackStatus.PROPOSED;
		item.instruction = instruction;
		item.proposalJson = proposalJson;
		item.requestedBy = actor;
		item.createdAt = now;
		item.updatedAt = now;
		return item;
	}

	public void apply(String verificationJson, String actor, Instant now) {
		require(WritebackStatus.PROPOSED);
		status = WritebackStatus.APPLIED;
		this.verificationJson = verificationJson;
		approvedBy = actor;
		updatedAt = now;
	}

	public void reject(String actor, Instant now) {
		require(WritebackStatus.PROPOSED);
		status = WritebackStatus.REJECTED;
		approvedBy = actor;
		updatedAt = now;
	}

	public void fail(Instant now) {
		require(WritebackStatus.PROPOSED);
		status = WritebackStatus.FAILED;
		updatedAt = now;
	}

	private void require(WritebackStatus expected) {
		if (status != expected) throw new IllegalStateException("현재 상태에서는 처리할 수 없습니다.");
	}

	public UUID getWritebackId() { return writebackId; }
	public UUID getAnalysisId() { return analysisId; }
	public WritebackStatus getStatus() { return status; }
	public String getInstruction() { return instruction; }
	public String getProposalJson() { return proposalJson; }
	public String getVerificationJson() { return verificationJson; }
	public String getRequestedBy() { return requestedBy; }
	public String getApprovedBy() { return approvedBy; }
	public Instant getCreatedAt() { return createdAt; }
	public Instant getUpdatedAt() { return updatedAt; }
}
