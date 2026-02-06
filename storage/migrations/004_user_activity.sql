-- User activity tracking and proactive insights

CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    query_type VARCHAR(50) NOT NULL,
    symbols TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS proactive_insights (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    insight_type VARCHAR(50) NOT NULL CHECK (insight_type IN (
        'portfolio_drift', 'earnings_upcoming', 'price_movement',
        'news_relevant', 'action_reminder', 'symbol_suggestion'
    )),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    symbols TEXT[] DEFAULT '{}',
    is_delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_activity_discord ON user_activity(discord_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_symbols ON user_activity USING GIN(symbols);
CREATE INDEX IF NOT EXISTS idx_proactive_undelivered ON proactive_insights(discord_id, is_delivered) WHERE is_delivered = FALSE;
