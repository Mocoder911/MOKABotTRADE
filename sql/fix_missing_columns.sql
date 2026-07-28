-- ═══════════════════════════════════════════════════════════════════════════════
-- FIX: Add missing columns to existing strategies table
-- Run this in Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════════

-- Add priority column if missing
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;

-- Add dry_run column if missing (safety: defaults to true)
ALTER TABLE strategies ADD COLUMN IF NOT EXISTS dry_run BOOLEAN DEFAULT true;

-- Add is_dry_run to execution_log if missing
ALTER TABLE execution_log ADD COLUMN IF NOT EXISTS is_dry_run BOOLEAN DEFAULT false;

-- Add profit_at_close to trades (stores profit when trade is closed)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS profit_at_close NUMERIC DEFAULT NULL;

-- Add closed_at to trades (used by bridge for close timestamp)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ DEFAULT NULL;

-- Add close_reason to trades
ALTER TABLE trades ADD COLUMN IF NOT EXISTS close_reason TEXT DEFAULT NULL;

-- Verify
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'strategies'
ORDER BY ordinal_position;
