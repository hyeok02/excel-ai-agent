CREATE SEQUENCE workbook_question_seq START WITH 1 INCREMENT BY 1 NOCYCLE;

CREATE TABLE workbook_questions (
    question_id NUMBER(19) NOT NULL,
    analysis_id RAW(16) NOT NULL,
    submitted_question CLOB NOT NULL,
    answer_json CLOB NOT NULL,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_workbook_questions PRIMARY KEY (question_id),
    CONSTRAINT fk_workbook_questions_job
        FOREIGN KEY (analysis_id) REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE,
    CONSTRAINT ck_workbook_questions_json CHECK (answer_json IS JSON)
);

CREATE INDEX ix_workbook_questions_analysis ON workbook_questions (analysis_id, question_id);
