-- Create a separate table for bot status to avoid any triggers on profiles
CREATE TABLE IF NOT EXISTS bot_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mt5_account_id TEXT NOT NULL UNIQUE,
    bot_active BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Insert initial record
INSERT INTO bot_status (mt5_account_id, bot_active)
VALUES ('260904217', false)
ON CONFLICT (mt5_account_id) DO NOTHING;

-- Disable RLS
ALTER TABLE bot_status DISABLE ROW LEVEL SECURITY;
