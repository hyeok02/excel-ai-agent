ALTER TABLE analysis_jobs ADD COLUMN owner_username VARCHAR(100);

CREATE INDEX idx_analysis_jobs_owner_created_at
    ON analysis_jobs (owner_username, created_at DESC);
