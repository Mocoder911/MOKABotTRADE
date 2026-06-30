-- ═══════════════════════════════════════════════════════════════════════════════
-- MOKABotTRADE — Generic Strategy Tables
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
  --     {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30},
  --     {"indicator": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_above", "compare_to": "signal"}
  --   ],
  --   "logic": "AND",
  --   "timeframe": "M15"
  -- }
  entry_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Exit rules (JSONB) — Same format as entry
  exit_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Position sizing (JSONB):
  -- {"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 0.5}
  -- {"mode": "fixed", "max_volume": 0.1}
  sizing_rules JSONB DEFAULT '{}'::jsonb,
  
  -- Filters (JSONB):
  -- {"max_spread_points": 30, "sessions": ["london", "new_york"]}
  filters JSONB DEFAULT '{}'::jsonb,
  
  -- Status
  is_active BOOLEAN DEFAULT false,
  priority INTEGER DEFAULT 0,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Audit Tables ─────────────────────────────────────────────────────────────
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

CREATE TABLE IF NOT EXISTS execution_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
  ticket TEXT,
  action TEXT NOT NULL,
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

-- ═══════════════════════════════════════════════════════════════════════════════
-- EXAMPLE STRATEGIES (Generic JSONB format)
-- ═══════════════════════════════════════════════════════════════════════════════

-- Strategy 1: RSI Oversold Buy
-- Change "value" from 30 to 25 → bot immediately uses 25
-- Change "indicator" from "rsi" to "stoch" → bot switches to Stochastic
INSERT INTO strategies (name, description, symbol, entry_rules, exit_rules, sizing_rules, filters, is_active)
VALUES (
  'RSI_Oversold_Buy',
  'Buy when RSI is oversold (below 30)',
  'XAUUSD',
  '{
    "conditions": [
      {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30}
    ],
    "logic": "AND",
    "timeframe": "M15"
  }'::jsonb,
  '{}'::jsonb,
  '{"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 0.5}'::jsonb,
  '{"max_spread_points": 50, "sessions": ["london", "new_york"]}'::jsonb,
  false
) ON CONFLICT (name) DO NOTHING;

-- Strategy 2: MACD + RSI Combo
-- Both conditions must be true (AND logic)
INSERT INTO strategies (name, description, symbol, entry_rules, exit_rules, sizing_rules, filters, is_active)
VALUES (
  'MACD_RSI_Combo',
  'Buy when MACD crosses above signal AND RSI < 40',
  'XAUUSD',
  '{
    "conditions": [
      {"indicator": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_above", "compare_to": "signal"},
      {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 40}
    ],
    "logic": "AND",
    "timeframe": "M15"
  }'::jsonb,
  '{}'::jsonb,
  '{"mode": "risk_percent", "risk_per_trade": 0.5, "max_volume": 0.3}'::jsonb,
  '{"max_spread_points": 30}'::jsonb,
  false
) ON CONFLICT (name) DO NOTHING;

-- Strategy 3: Bollinger Bands Bounce
INSERT INTO strategies (name, description, symbol, entry_rules, exit_rules, sizing_rules, filters, is_active)
VALUES (
  'BB_Lower_Bounce',
  'Buy when price touches lower Bollinger Band',
  'XAUUSD',
  '{
    "conditions": [
      {"indicator": "bbands", "params": {"length": 20, "std": 2}, "operator": "lt", "value": 0, "compare_to": "lower"}
    ],
    "logic": "AND",
    "timeframe": "M15"
  }'::jsonb,
  '{}'::jsonb,
  '{"mode": "risk_percent", "risk_per_trade": 1.0, "max_volume": 0.5}'::jsonb,
  '{}'::jsonb,
  false
) ON CONFLICT (name) DO NOTHING;

-- ─── Verify ───────────────────────────────────────────────────────────────────
SELECT name, symbol, is_active, entry_rules->>'conditions' as conditions FROM strategies;
