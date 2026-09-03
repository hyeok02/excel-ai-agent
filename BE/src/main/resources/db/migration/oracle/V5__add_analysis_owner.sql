ALTER TABLE analysis_jobs ADD (owner_username VARCHAR2(100 CHAR));

CREATE INDEX idx_analysis_jobs_owner_created_at
    ON analysis_jobs (owner_username, created_at DESC);
