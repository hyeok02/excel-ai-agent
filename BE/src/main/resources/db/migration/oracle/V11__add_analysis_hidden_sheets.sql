ALTER TABLE analysis_jobs
    ADD include_hidden_sheets NUMBER(1, 0) DEFAULT 0 NOT NULL;

ALTER TABLE analysis_jobs
    ADD CONSTRAINT ck_analysis_hidden_sheets CHECK (include_hidden_sheets IN (0, 1));
