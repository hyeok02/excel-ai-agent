CREATE TABLE telegram_recipients (
    recipient_id RAW(16) NOT NULL,
    owner_username VARCHAR2(100 CHAR) NOT NULL,
    chat_id VARCHAR2(32 CHAR) NOT NULL,
    telegram_user_id VARCHAR2(32 CHAR) NOT NULL,
    telegram_username VARCHAR2(255 CHAR),
    first_name VARCHAR2(255 CHAR),
    last_name VARCHAR2(255 CHAR),
    display_name VARCHAR2(255 CHAR) NOT NULL,
    active NUMBER(1, 0) DEFAULT 1 NOT NULL,
    connected_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_telegram_recipients PRIMARY KEY (recipient_id),
    CONSTRAINT uk_telegram_recip_owner_chat UNIQUE (owner_username, chat_id),
    CONSTRAINT ck_telegram_recipients_active CHECK (active IN (0, 1))
);

CREATE INDEX idx_telegram_recip_owner_active
    ON telegram_recipients (owner_username, active, connected_at DESC);

CREATE TABLE telegram_recipient_invites (
    invite_id RAW(16) NOT NULL,
    owner_username VARCHAR2(100 CHAR) NOT NULL,
    label VARCHAR2(255 CHAR),
    token_hash VARCHAR2(64 CHAR) NOT NULL,
    recipient_id RAW(16),
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP(6) WITH TIME ZONE,
    revoked_at TIMESTAMP(6) WITH TIME ZONE,
    CONSTRAINT pk_telegram_recipient_invites PRIMARY KEY (invite_id),
    CONSTRAINT uk_telegram_invites_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_telegram_invites_recipient FOREIGN KEY (recipient_id)
        REFERENCES telegram_recipients (recipient_id) ON DELETE SET NULL
);

CREATE INDEX idx_telegram_invites_owner_created
    ON telegram_recipient_invites (owner_username, created_at DESC);
