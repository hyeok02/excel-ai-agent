CREATE TABLE workbook_writebacks (
    writeback_id UUID PRIMARY KEY,
    analysis_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL,
    instruction VARCHAR(1000) NOT NULL,
    proposal_json CLOB NOT NULL,
    verification_json CLOB,
    requested_by VARCHAR(100) NOT NULL,
    approved_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT fk_writebacks_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE
);

CREATE INDEX idx_writebacks_analysis_created
    ON workbook_writebacks (analysis_id, created_at DESC);
