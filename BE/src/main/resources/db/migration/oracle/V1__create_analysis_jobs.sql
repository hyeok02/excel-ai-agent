CREATE TABLE analysis_jobs (
    analysis_id RAW(16) NOT NULL,
    status VARCHAR2(20 CHAR) NOT NULL,
    analysis_mode VARCHAR2(20 CHAR) NOT NULL,
    original_filename VARCHAR2(255 CHAR) NOT NULL,
    file_extension VARCHAR2(10 CHAR) NOT NULL,
    file_size_bytes NUMBER(19, 0) NOT NULL,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_analysis_jobs PRIMARY KEY (analysis_id)
);

CREATE INDEX idx_analysis_jobs_created_at
    ON analysis_jobs (created_at DESC);
