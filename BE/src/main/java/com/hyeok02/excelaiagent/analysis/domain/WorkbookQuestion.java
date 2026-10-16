package com.hyeok02.excelaiagent.analysis.domain;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.SequenceGenerator;
import jakarta.persistence.Table;

/** The immutable answer snapshot, not a newly generated or re-verified answer. */
@Entity
@Table(name = "workbook_questions")
public class WorkbookQuestion {

	@Id
	@GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "workbook_question_ids")
	@SequenceGenerator(name = "workbook_question_ids", sequenceName = "workbook_question_seq", allocationSize = 1)
	@Column(name = "question_id", nullable = false, updatable = false)
	private Long id;

	@Column(name = "analysis_id", nullable = false, updatable = false)
	private UUID analysisId;

	@Lob
	@Column(name = "submitted_question", nullable = false, updatable = false)
	private String submittedQuestion;

	@Lob
	@Column(name = "answer_json", nullable = false, updatable = false)
	private String answerJson;

	@Column(name = "created_at", nullable = false, updatable = false)
	private Instant createdAt;

	protected WorkbookQuestion() {
	}

	public static WorkbookQuestion answered(
			UUID analysisId, String submittedQuestion, String answerJson, Instant createdAt) {
		WorkbookQuestion question = new WorkbookQuestion();
		question.analysisId = analysisId;
		question.submittedQuestion = submittedQuestion;
		question.answerJson = answerJson;
		question.createdAt = createdAt;
		return question;
	}

	public Long getId() { return id; }
	public UUID getAnalysisId() { return analysisId; }
	public String getSubmittedQuestion() { return submittedQuestion; }
	public String getAnswerJson() { return answerJson; }
	public Instant getCreatedAt() { return createdAt; }
}
