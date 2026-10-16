CREATE SEQUENCE workbook_question_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE workbook_questions (
    question_id BIGINT PRIMARY KEY,
    analysis_id UUID NOT NULL,
    submitted_question CLOB NOT NULL,
    answer_json CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT fk_workbook_questions_job
        FOREIGN KEY (analysis_id) REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE
);

CREATE INDEX ix_workbook_questions_analysis ON workbook_questions (analysis_id, question_id);
