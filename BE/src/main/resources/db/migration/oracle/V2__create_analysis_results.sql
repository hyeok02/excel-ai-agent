CREATE TABLE analysis_results (
    analysis_id RAW(16) NOT NULL,
    result_json CLOB NOT NULL,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_analysis_results PRIMARY KEY (analysis_id),
    CONSTRAINT fk_analysis_results_job
        FOREIGN KEY (analysis_id) REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE,
    CONSTRAINT ck_analysis_results_json CHECK (result_json IS JSON)
);
