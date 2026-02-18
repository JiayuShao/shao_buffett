-- Remove polymarket_signal from proactive_insights CHECK constraint

ALTER TABLE proactive_insights DROP CONSTRAINT IF EXISTS proactive_insights_insight_type_check;
ALTER TABLE proactive_insights ADD CONSTRAINT proactive_insights_insight_type_check
    CHECK (insight_type IN (
        'portfolio_drift', 'earnings_upcoming', 'price_movement',
        'news_relevant', 'action_reminder', 'symbol_suggestion',
        'earnings_calendar', 'insider_trade', 'earnings_analysis'
    ));
