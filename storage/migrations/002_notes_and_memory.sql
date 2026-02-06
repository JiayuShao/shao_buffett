-- Conversation notes for cross-conversation memory

CREATE TABLE IF NOT EXISTS conversation_notes (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    note_type VARCHAR(20) NOT NULL CHECK (note_type IN ('insight', 'decision', 'action_item', 'preference', 'concern')),
    content TEXT NOT NULL,
    symbols TEXT[] DEFAULT '{}',
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notes_discord_id ON conversation_notes(discord_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_type ON conversation_notes(discord_id, note_type) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_notes_symbols ON conversation_notes USING GIN(symbols);
