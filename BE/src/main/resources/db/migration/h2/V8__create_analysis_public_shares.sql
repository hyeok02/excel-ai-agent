CREATE TABLE analysis_public_shares (
    share_id UUID PRIMARY KEY,
    analysis_id UUID NOT NULL,
    recipient_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uk_analysis_public_share_token UNIQUE (token_hash),
    CONSTRAINT fk_public_shares_analysis FOREIGN KEY (analysis_id)
        REFERENCES analysis_jobs (analysis_id) ON DELETE CASCADE,
    CONSTRAINT fk_public_shares_recipient FOREIGN KEY (recipient_id)
        REFERENCES telegram_recipients (recipient_id) ON DELETE CASCADE
);

CREATE INDEX idx_public_shares_recipient
    ON analysis_public_shares (recipient_id, created_at DESC);

CREATE INDEX idx_public_shares_expiry
    ON analysis_public_shares (expires_at, revoked_at);
