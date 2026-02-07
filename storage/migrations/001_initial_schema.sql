-- Shao Buffett initial schema

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    interests JSONB DEFAULT '{}',
    focused_metrics JSONB DEFAULT '["pe_ratio","revenue_growth","eps","dividend_yield"]',
    notification_preferences JSONB DEFAULT '{"delivery":"channel","quiet_hours":null}',
    risk_tolerance TEXT DEFAULT 'moderate',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(discord_id, symbol)
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    condition VARCHAR(20) NOT NULL,
    threshold DECIMAL NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    model_used VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dashboards (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    channel_id BIGINT,
    message_id BIGINT,
    auto_refresh_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    symbol VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_watchlists_discord_id ON watchlists(discord_id);
CREATE INDEX IF NOT EXISTS idx_price_alerts_active ON price_alerts(discord_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_conversations_user_channel ON conversations(discord_id, channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_log_hash ON notification_log(content_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_cache_expires ON data_cache(expires_at);
