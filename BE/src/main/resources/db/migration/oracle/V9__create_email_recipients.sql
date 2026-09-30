CREATE TABLE email_recipients (
    recipient_id RAW(16) NOT NULL,
    owner_username VARCHAR2(100 CHAR) NOT NULL,
    email VARCHAR2(255 CHAR) NOT NULL,
    display_name VARCHAR2(255 CHAR) NOT NULL,
    active NUMBER(1, 0) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_email_recipients PRIMARY KEY (recipient_id),
    CONSTRAINT uk_email_recipients_owner_email UNIQUE (owner_username, email),
    CONSTRAINT ck_email_recipients_active CHECK (active IN (0, 1))
);

CREATE INDEX idx_email_recipients_owner_active
    ON email_recipients (owner_username, active, created_at DESC);

ALTER TABLE analysis_public_shares
    MODIFY (recipient_id NULL);

ALTER TABLE analysis_public_shares
    ADD (email_recipient_id RAW(16));

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
