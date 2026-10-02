ALTER TABLE analysis_jobs
    ADD COLUMN include_hidden_sheets BOOLEAN DEFAULT FALSE NOT NULL;
