CREATE TABLE workbook_writebacks (
    writeback_id RAW(16) NOT NULL,
    analysis_id RAW(16) NOT NULL,
    status VARCHAR2(20) NOT NULL,
    instruction VARCHAR2(1000) NOT NULL,
    proposal_json CLOB NOT NULL,
    verification_json CLOB,
    requested_by VARCHAR2(100) NOT NULL,
    approved_by VARCHAR2(100),
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_workbook_writebacks PRIMARY KEY (writeback_id),
    CONSTRAINT fk_writebacks_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE,
    CONSTRAINT ck_writeback_proposal_json CHECK (proposal_json IS JSON),
    CONSTRAINT ck_writeback_verification_json
        CHECK (verification_json IS NULL OR verification_json IS JSON)
);

CREATE INDEX idx_writebacks_analysis_created
    ON workbook_writebacks (analysis_id, created_at DESC);
