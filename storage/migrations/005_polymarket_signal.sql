-- Add polymarket_signal insight type and content_hash for deduplication

-- Recreate the CHECK constraint to include polymarket_signal
ALTER TABLE proactive_insights DROP CONSTRAINT IF EXISTS proactive_insights_insight_type_check;
ALTER TABLE proactive_insights ADD CONSTRAINT proactive_insights_insight_type_check
    CHECK (insight_type IN (
        'portfolio_drift', 'earnings_upcoming', 'price_movement',
        'news_relevant', 'action_reminder', 'symbol_suggestion',
        'polymarket_signal'
    ));

-- Add content_hash column for deduplication
ALTER TABLE proactive_insights ADD COLUMN IF NOT EXISTS content_hash VARCHAR(16);

-- Index for fast dedup lookups
CREATE INDEX IF NOT EXISTS idx_proactive_dedup
    ON proactive_insights(discord_id, insight_type, content_hash, created_at DESC);
