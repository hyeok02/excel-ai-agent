ALTER TABLE workbook_writebacks
    ADD COLUMN base_writeback_id UUID;

ALTER TABLE workbook_writebacks
    ADD CONSTRAINT fk_writebacks_base FOREIGN KEY (base_writeback_id)
        REFERENCES workbook_writebacks (writeback_id) ON DELETE SET NULL;

CREATE INDEX idx_writebacks_analysis_status
    ON workbook_writebacks (analysis_id, status, updated_at DESC);
