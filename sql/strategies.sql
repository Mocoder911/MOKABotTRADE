-- ═══════════════════════════════════════════════════════════════════════════════
-- MOKABotTRADE — Strategies & Rules Tables
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Strategies Table ─────────────────────────────────────────────────────────
-- Contains trading strategies with entry/exit rules stored as JSON
CREATE TABLE IF NOT EXISTS strategies (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  symbol TEXT NOT NULL,
  timeframe TEXT DEFAULT 'M15',
  
  -- Entry conditions (JSON): defines when to open a trade
  -- Example: {"indicators": ["RSI < 30", "MACD > Signal"], "pattern": "bullish_engulfing"}
  entry_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Exit conditions (JSON): defines when to close/modify
  -- Example: {"take_profit": "tp_points", "stop_loss": "sl_points", "trailing": true}
  exit_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Position sizing rules (JSON)
  -- Example: {"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 1.0}
  sizing_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Filters (JSON): additional conditions to check
  -- Example: {"max_spread": 30, "session": "london,new_york", "min_volatility": 0.5}
  filters JSONB DEFAULT '{}'::jsonb,
  
  -- Status
  is_active BOOLEAN DEFAULT false,
  priority INTEGER DEFAULT 0,  -- Higher = checked first
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Trade Signals Table ──────────────────────────────────────────────────────
-- Stores signals detected by the bot (for audit/debugging)
CREATE TABLE IF NOT EXISTS trade_signals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  signal_type TEXT NOT NULL,  -- 'ENTRY_BUY', 'ENTRY_SELL', 'EXIT', 'MODIFY'
  signal_data JSONB DEFAULT '{}'::jsonb,
  action_taken TEXT,  -- 'EXECUTED', 'SKIPPED', 'FAILED'
  action_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Execution Log Table ──────────────────────────────────────────────────────
-- Logs all trade executions for audit
CREATE TABLE IF NOT EXISTS execution_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  ticket TEXT,
  action TEXT NOT NULL,  -- 'OPEN', 'CLOSE', 'MODIFY'
  symbol TEXT,
  volume DECIMAL(10,2),
  price DECIMAL(15,5),
  sl DECIMAL(15,5),
  tp DECIMAL(15,5),
  result JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Disable RLS ──────────────────────────────────────────────────────────────
ALTER TABLE strategies DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_signals DISABLE ROW LEVEL SECURITY;
ALTER TABLE execution_log DISABLE ROW LEVEL SECURITY;

-- ─── Example Strategy ─────────────────────────────────────────────────────────
-- Insert a sample strategy (you can modify via dashboard)
INSERT INTO strategies (name, description, symbol, entry_rules, exit_rules, sizing_rules, filters, is_active)
VALUES (
  'RSI_Reversal',
  'Buy when RSI < 30 and MACD crosses above signal',
  'XAUUSD',
  '{"indicators": [{"name": "RSI", "condition": "less_than", "value": 30}, {"name": "MACD", "condition": "crosses_above", "compare": "signal"}], "timeframe": "M15"}'::jsonb,
  '{"take_profit": "use_risk_matrix", "stop_loss": "use_risk_matrix", "breakeven": "use_risk_matrix"}'::jsonb,
  '{"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 0.5}'::jsonb,
  '{"max_spread_points": 30, "sessions": ["london", "new_york"]}'::jsonb,
  false  -- Start inactive
)
ON CONFLICT (name) DO NOTHING;

-- ─── Verify ───────────────────────────────────────────────────────────────────
SELECT * FROM strategies;
