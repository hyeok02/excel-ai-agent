CREATE TABLE analysis_results (
    analysis_id UUID PRIMARY KEY,
    result_json CLOB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT fk_analysis_results_job
        FOREIGN KEY (analysis_id) REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE
);
