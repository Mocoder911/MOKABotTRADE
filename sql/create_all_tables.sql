-- ═══════════════════════════════════════════════════════════════════════════════
-- MOKABotTRADE — Complete Strategy Tables Setup
-- Run this ONCE in Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Strategies Table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategies (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  symbol TEXT NOT NULL,
  
  -- Entry rules (JSONB) — Generic format:
  -- {
  --   "conditions": [
  --     {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30}
  --   ],
  --   "logic": "AND",
  --   "timeframe": "M15"
  -- }
  entry_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Exit rules (JSONB)
  exit_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Position sizing (JSONB):
  -- {"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 0.5}
  sizing_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Filters (JSONB):
  -- {"max_spread_points": 30, "sessions": ["london", "new_york"]}
  filters JSONB DEFAULT '{}'::jsonb,
  
  -- Status
  is_active BOOLEAN DEFAULT false,
  priority INTEGER DEFAULT 0,
  
  -- Dry Run Mode: When true, bot simulates trades without executing
  dry_run BOOLEAN DEFAULT true,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Trade Signals Table ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_signals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  signal_data JSONB DEFAULT '{}'::jsonb,
  action_taken TEXT,
  action_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Execution Log Table ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS execution_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  ticket TEXT,
  action TEXT NOT NULL,  -- 'OPEN', 'CLOSE', 'MODIFY', 'SIMULATED'
  symbol TEXT,
  volume DECIMAL(10,2),
  price DECIMAL(15,5),
  sl DECIMAL(15,5),
  tp DECIMAL(15,5),
  result JSONB DEFAULT '{}'::jsonb,
  is_dry_run BOOLEAN DEFAULT false,  -- True if this was a simulated trade
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Disable RLS ──────────────────────────────────────────────────────────────
ALTER TABLE strategies DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_signals DISABLE ROW LEVEL SECURITY;
ALTER TABLE execution_log DISABLE ROW LEVEL SECURITY;

-- ─── Verify ───────────────────────────────────────────────────────────────────
SELECT 'strategies' as table_name, count(*) as row_count FROM strategies
UNION ALL
SELECT 'trade_signals', count(*) FROM trade_signals
UNION ALL
SELECT 'execution_log', count(*) FROM execution_log;
