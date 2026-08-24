CREATE TABLE app_users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(100),
    display_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    user_role VARCHAR(20) NOT NULL,
    auth_provider VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uk_app_users_username UNIQUE (username),
    CONSTRAINT uk_app_users_email UNIQUE (email)
);

CREATE INDEX idx_app_users_created_at ON app_users (created_at DESC);
