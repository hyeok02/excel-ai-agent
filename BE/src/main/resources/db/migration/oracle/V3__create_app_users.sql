CREATE TABLE app_users (
    user_id RAW(16) NOT NULL,
    username VARCHAR2(100 CHAR) NOT NULL,
    password_hash VARCHAR2(100 CHAR),
    display_name VARCHAR2(100 CHAR) NOT NULL,
    email VARCHAR2(255 CHAR),
    user_role VARCHAR2(20 CHAR) NOT NULL,
    auth_provider VARCHAR2(20 CHAR) NOT NULL,
    enabled NUMBER(1, 0) DEFAULT 1 NOT NULL,
    created_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP(6) WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_app_users PRIMARY KEY (user_id),
    CONSTRAINT uk_app_users_username UNIQUE (username),
    CONSTRAINT uk_app_users_email UNIQUE (email),
    CONSTRAINT ck_app_users_enabled CHECK (enabled IN (0, 1))
);

CREATE INDEX idx_app_users_created_at ON app_users (created_at DESC);
