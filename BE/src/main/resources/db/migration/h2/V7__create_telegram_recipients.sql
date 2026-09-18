CREATE TABLE telegram_recipients (
    recipient_id UUID PRIMARY KEY,
    owner_username VARCHAR(100) NOT NULL,
    chat_id VARCHAR(32) NOT NULL,
    telegram_user_id VARCHAR(32) NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    display_name VARCHAR(255) NOT NULL,
    active BOOLEAN NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_telegram_recipients_owner_chat UNIQUE (owner_username, chat_id)
);

CREATE INDEX idx_telegram_recipients_owner_active
    ON telegram_recipients (owner_username, active, connected_at DESC);

CREATE TABLE telegram_recipient_invites (
    invite_id UUID PRIMARY KEY,
    owner_username VARCHAR(100) NOT NULL,
    label VARCHAR(255),
    token_hash VARCHAR(64) NOT NULL,
    recipient_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uk_telegram_invites_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_telegram_invites_recipient FOREIGN KEY (recipient_id)
        REFERENCES telegram_recipients (recipient_id) ON DELETE SET NULL
);

CREATE INDEX idx_telegram_invites_owner_created
    ON telegram_recipient_invites (owner_username, created_at DESC);
