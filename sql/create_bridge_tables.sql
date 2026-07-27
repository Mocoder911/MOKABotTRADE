-- ═══════════════════════════════════════════════════════════════════════════════
-- Bridge Control Center Tables
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. Bridge Commands - Command queue (dashboard writes, bridge reads/consumes)
CREATE TABLE IF NOT EXISTS bridge_commands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mt5_account_id TEXT NOT NULL,
    command TEXT NOT NULL CHECK (command IN ('RESTART', 'STOP', 'STATUS')),
    payload JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT now(),
    executed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_bridge_commands_pending 
    ON bridge_commands(mt5_account_id, status) 
    WHERE status = 'pending';

ALTER TABLE bridge_commands DISABLE ROW LEVEL SECURITY;

-- 2. Bridge Logs - Log storage (bridge writes, dashboard reads)
CREATE TABLE IF NOT EXISTS bridge_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mt5_account_id TEXT NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bridge_logs_lookup 
    ON bridge_logs(mt5_account_id, created_at DESC);

ALTER TABLE bridge_logs DISABLE ROW LEVEL SECURITY;

-- 3. Bridge Heartbeat - Heartbeat tracking (bridge updates each cycle)
CREATE TABLE IF NOT EXISTS bridge_heartbeat (
    mt5_account_id TEXT PRIMARY KEY,
    last_heartbeat TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'stopped' CHECK (status IN ('running', 'stopped', 'error')),
    cycle_count INT DEFAULT 0,
    uptime_since TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE bridge_heartbeat DISABLE ROW LEVEL SECURITY;

-- Insert initial heartbeat record for existing account
INSERT INTO bridge_heartbeat (mt5_account_id, status, cycle_count) 
VALUES ('260904217', 'stopped', 0)
ON CONFLICT (mt5_account_id) DO NOTHING;
