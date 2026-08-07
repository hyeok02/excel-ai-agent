CREATE TABLE analysis_jobs (
    analysis_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    analysis_mode VARCHAR(20) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_analysis_jobs_created_at
    ON analysis_jobs (created_at DESC);
