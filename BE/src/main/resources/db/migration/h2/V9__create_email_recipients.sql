CREATE TABLE email_recipients (
    recipient_id UUID PRIMARY KEY,
    owner_username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_email_recipients_owner_email UNIQUE (owner_username, email)
);

CREATE INDEX idx_email_recipients_owner_active
    ON email_recipients (owner_username, active, created_at DESC);

ALTER TABLE analysis_public_shares
    ALTER COLUMN recipient_id DROP NOT NULL;

ALTER TABLE analysis_public_shares
    ADD COLUMN email_recipient_id UUID;

ALTER TABLE analysis_public_shares
    ADD CONSTRAINT fk_public_shares_email_recipient
        FOREIGN KEY (email_recipient_id)
        REFERENCES email_recipients (recipient_id) ON DELETE CASCADE;

ALTER TABLE analysis_public_shares
    ADD CONSTRAINT ck_public_shares_one_recipient CHECK (
        (recipient_id IS NOT NULL AND email_recipient_id IS NULL)
        OR (recipient_id IS NULL AND email_recipient_id IS NOT NULL)
    );

CREATE INDEX idx_public_shares_email_recipient
    ON analysis_public_shares (email_recipient_id, created_at DESC);
