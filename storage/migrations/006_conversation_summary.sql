-- Add summary flag to conversations table for compressed history
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_summary BOOLEAN DEFAULT FALSE;
