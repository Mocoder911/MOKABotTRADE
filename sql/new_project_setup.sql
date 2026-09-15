-- ============================================================================
-- MOKABotTRADE — COMPLETE DATABASE SETUP (Fresh Project)
-- ============================================================================
-- Run this ONCE in Supabase SQL Editor after creating a new project.
-- Creates ALL tables, triggers, indexes, and seed data needed by:
--   - mt5_bridge_multi.py (Python trading bot)
--   - Next.js frontend (dashboard / API routes)
--   - Bridge Console (command queue / heartbeat / logs)
--
-- Total tables: 15
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. PROFILES — User accounts + MT5 credentials
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email               TEXT UNIQUE NOT NULL,
  full_name           TEXT DEFAULT '',
  role                TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  status              TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended')),
  mt5_account_id      TEXT,
  mt5_password        TEXT,
  mt5_server          TEXT,
  bot_active          BOOLEAN DEFAULT false,
  verification_status TEXT DEFAULT 'PENDING' CHECK (verification_status IN ('PENDING', 'VALIDATED', 'INVALID_CREDENTIALS')),
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. BOT_STATUS — Bot active/inactive flag per MT5 account
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_status (
  mt5_account_id TEXT PRIMARY KEY,
  bot_active     BOOLEAN DEFAULT false,
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE bot_status DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. TRADES — Open & closed trade records
--    NOTE: Uses account_id (TEXT) to match Python bridge field name
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
  id              BIGSERIAL PRIMARY KEY,
  ticket          TEXT UNIQUE NOT NULL,
  user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  account_id      TEXT,
  symbol          TEXT NOT NULL,
  type            TEXT NOT NULL CHECK (type IN ('BUY', 'SELL')),
  volume          NUMERIC NOT NULL DEFAULT 0,
  entry           NUMERIC NOT NULL DEFAULT 0,
  sl              NUMERIC DEFAULT 0,
  tp              NUMERIC DEFAULT 0,
  live_pl         NUMERIC DEFAULT 0,
  margin          NUMERIC DEFAULT 0,
  open_time       TIMESTAMPTZ,
  close_time      TIMESTAMPTZ,
  closed_at       TIMESTAMPTZ DEFAULT NULL,
  status          TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  profit_at_close NUMERIC DEFAULT NULL,
  close_reason    TEXT DEFAULT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_trades_account_status ON trades(account_id, status);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id);
ALTER TABLE trades DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. STRATEGIES — Generic strategy definitions (JSONB rules)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategies (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id       UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name          TEXT NOT NULL UNIQUE,
  description   TEXT DEFAULT '',
  symbol        TEXT NOT NULL DEFAULT 'ALL',
  entry_rules   JSONB DEFAULT '{}'::jsonb,
  exit_rules    JSONB DEFAULT '{}'::jsonb,
  sizing_rules  JSONB DEFAULT '{}'::jsonb,
  filters       JSONB DEFAULT '{}'::jsonb,
  config        JSONB DEFAULT '{}'::jsonb,
  is_active     BOOLEAN DEFAULT false,
  priority      INTEGER DEFAULT 0,
  dry_run       BOOLEAN DEFAULT true,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE strategies DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. TRADE_SIGNALS — Signal audit log
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_signals (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id   UUID REFERENCES strategies(id) ON DELETE CASCADE,
  symbol        TEXT NOT NULL,
  signal_type   TEXT NOT NULL,
  signal_data   JSONB DEFAULT '{}'::jsonb,
  action_taken  TEXT,
  action_reason TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE trade_signals DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. EXECUTION_LOG — Trade execution audit log
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS execution_log (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  strategy_id   UUID REFERENCES strategies(id) ON DELETE CASCADE,
  ticket        TEXT,
  action        TEXT NOT NULL CHECK (action IN ('OPEN', 'CLOSE', 'MODIFY', 'SIMULATED')),
  symbol        TEXT,
  volume        DECIMAL(10,2),
  price         DECIMAL(15,5),
  sl            DECIMAL(15,5),
  tp            DECIMAL(15,5),
  result        JSONB DEFAULT '{}'::jsonb,
  is_dry_run    BOOLEAN DEFAULT false,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE execution_log DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. RISK_MATRIX — Per-symbol risk configuration
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_matrix (
  id                BIGSERIAL PRIMARY KEY,
  user_id           UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  symbol            TEXT NOT NULL,
  risk_level        TEXT DEFAULT 'medium',
  max_position_size NUMERIC DEFAULT 0,
  stop_loss_pct     NUMERIC DEFAULT 0,
  take_profit_pct   NUMERIC DEFAULT 0,
  config            JSONB DEFAULT '{}',
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE risk_matrix DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. BRIDGE_LOGS — Log storage (bridge writes, dashboard reads)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_logs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mt5_account_id  TEXT NOT NULL,
  level           TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
  message         TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bridge_logs_lookup ON bridge_logs(mt5_account_id, created_at DESC);
ALTER TABLE bridge_logs DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. BRIDGE_HEARTBEAT — Heartbeat tracking (bridge updates each cycle)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_heartbeat (
  mt5_account_id  TEXT PRIMARY KEY,
  last_heartbeat  TIMESTAMPTZ DEFAULT NOW(),
  status          TEXT DEFAULT 'stopped' CHECK (status IN ('running', 'stopped', 'error')),
  cycle_count     INT DEFAULT 0,
  uptime_since    TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE bridge_heartbeat DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. BRIDGE_COMMANDS — Command queue (dashboard writes, bridge reads)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_commands (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mt5_account_id  TEXT NOT NULL,
  command         TEXT NOT NULL CHECK (command IN ('RESTART', 'STOP', 'STATUS')),
  payload         JSONB DEFAULT '{}',
  status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'failed')),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  executed_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_bridge_commands_pending ON bridge_commands(mt5_account_id, status) WHERE status = 'pending';
ALTER TABLE bridge_commands DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 11. ACCOUNT_METRICS — Historical account metrics
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_metrics (
  id              BIGSERIAL PRIMARY KEY,
  user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  mt5_account_id  TEXT,
  balance         NUMERIC DEFAULT 0,
  equity          NUMERIC DEFAULT 0,
  margin          NUMERIC DEFAULT 0,
  free_margin     NUMERIC DEFAULT 0,
  profit          NUMERIC DEFAULT 0,
  recorded_at     TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE account_metrics DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 12. ACCOUNT_BALANCE — Current balance (upsert by user_id)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_balance (
  id          BIGSERIAL PRIMARY KEY,
  user_id     TEXT NOT NULL UNIQUE,
  balance     NUMERIC DEFAULT 0,
  equity      NUMERIC DEFAULT 0,
  margin      NUMERIC DEFAULT 0,
  free_margin NUMERIC DEFAULT 0,
  profit      NUMERIC DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE account_balance DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 13. TODAY_NET — Daily net profit (calculated by bridge)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS today_net (
  id            BIGSERIAL PRIMARY KEY,
  user_id       UUID NOT NULL,
  account_id    TEXT NOT NULL,
  net_profit    DECIMAL(10, 2) NOT NULL DEFAULT 0,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  date          DATE NOT NULL DEFAULT CURRENT_DATE
);
CREATE INDEX IF NOT EXISTS idx_today_net_user_date ON today_net(user_id, date);
ALTER TABLE today_net DISABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 14. TACTICS_SETTINGS — Key-value store for strategy parameters
--     Used by Python bridge to read runtime config (lot size, basket TP, etc.)
--     Values stored as JSONB: {"value": <actual_value>}
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tactics_settings (
  id          BIGSERIAL PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  key         TEXT NOT NULL UNIQUE,
  value       JSONB DEFAULT '{}'::jsonb,
  description TEXT DEFAULT '',
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE tactics_settings DISABLE ROW LEVEL SECURITY;

-- Insert default FTMO challenge settings (all values as JSONB objects)
INSERT INTO tactics_settings (key, value, description) VALUES
  ('Fixed_Lot_Size',         '{"value": 0.03}'::jsonb,                  'Position lot size'),
  ('Basket_Take_Profit',     '{"value": 10.0}'::jsonb,                  'Basket TP per pair in USD'),
  ('Grid_Step',              '{"value": 100}'::jsonb,                   'Grid step in points'),
  ('Grid_Step_Loss_USD',     '{"value": 15.0}'::jsonb,                  'Grid trigger: pair net floating loss USD'),
  ('Max_Open_Positions',     '{"value": 20}'::jsonb,                    'Max base positions across all pairs'),
  ('Freeze_Drawdown',        '{"value": -3500.0}'::jsonb,               'Freeze engine threshold'),
  ('Max_Spread_Pips',        '{"value": 3.0}'::jsonb,                   'Max allowed spread in pips'),
  ('Execution_Delay_Ms',     '{"value": 500}'::jsonb,                   'Delay between orders in ms'),
  ('Allowed_Pairs',          '{"value": "EURUSD,GBPUSD,USDCAD,USDJPY,AUDUSD,NZDUSD"}'::jsonb, 'Comma-separated allowed pairs'),
  ('kill_switch',            '{"value": false}'::jsonb,                  'Emergency kill switch'),
  ('risk_per_trade',         '{"value": 1, "unit": "percent"}'::jsonb,  'Risk per trade'),
  ('max_daily_trades',       '{"value": 100}'::jsonb,                   'Max daily trades'),
  ('Enable_Restricted_Symbols', '{"value": false}'::jsonb,              'Enable restricted symbols'),
  ('Excluded_Symbols',       '{"value": ""}'::jsonb,                    'Excluded symbols list'),
  ('Equity_Stop_Loss_Pct',   '{"value": 0}'::jsonb,                    'Equity stop loss percentage (0=disabled)')
ON CONFLICT (key) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 15. GRID_CONFIG — Grid EA configuration per MT5 account
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grid_config (
  id              BIGSERIAL PRIMARY KEY,
  mt5_account_id  TEXT NOT NULL UNIQUE,
  lot_size        DOUBLE PRECISION NOT NULL DEFAULT 0.03,
  grid_step       INTEGER NOT NULL DEFAULT 100,
  max_orders      INTEGER NOT NULL DEFAULT 20,
  basket_profit   DOUBLE PRECISION NOT NULL DEFAULT 10.0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE grid_config DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- TRIGGER: Auto-create profile when new user signs up
-- ============================================================================
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, role, status)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    'user',
    'pending'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Profile auto-creation failed: %', SQLERRM;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- CLEANUP: Remove any broken hooks from supabase_functions
-- ============================================================================
DELETE FROM supabase_functions.hooks;

-- ============================================================================
-- VERIFICATION — Run these to confirm everything is set up correctly
-- ============================================================================
SELECT '=== TABLES CREATED ===' as info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

SELECT '=== TACTICS SETTINGS ===' as info;
SELECT key, value FROM tactics_settings ORDER BY key;

SELECT '=== TRIGGERS ===' as info;
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';

-- ============================================================================
-- RELOAD SCHEMA — Tell Supabase PostgREST to pick up new tables
-- ============================================================================
NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- DONE! Database is ready.
-- ============================================================================

-- ─── ADMIN SETUP (uncomment after creating the user above) ──────────────────
-- UPDATE profiles 
-- SET role = 'admin', status = 'active', verification_status = 'VALIDATED', bot_active = true
-- WHERE email = 'moss911.moss@gmail.com';

-- ─── INSERT MT5 ACCOUNT (uncomment and fill in your FTMO credentials) ───────
-- UPDATE profiles 
-- SET mt5_account_id = '1514628159', 
--     mt5_password = '@FiKx4i$RCF', 
--     mt5_server = 'FTMO-Demo',
--     verification_status = 'VALIDATED',
--     bot_active = true
-- WHERE email = 'moss911.moss@gmail.com';

-- ─── INSERT GRID CONFIG (uncomment after getting your user_id) ──────────────
-- INSERT INTO grid_config (mt5_account_id, lot_size, grid_step, max_orders, basket_profit)
-- VALUES ('1514628159', 0.03, 100, 20, 10.0)
-- ON CONFLICT (mt5_account_id) DO NOTHING;

-- ─── INSERT BRIDGE HEARTBEAT (uncomment) ────────────────────────────────────
-- INSERT INTO bridge_heartbeat (mt5_account_id, status, cycle_count)
-- VALUES ('1514628159', 'stopped', 0)
-- ON CONFLICT (mt5_account_id) DO NOTHING;

-- ─── INSERT BOT STATUS (uncomment) ──────────────────────────────────────────
-- INSERT INTO bot_status (mt5_account_id, bot_active)
-- VALUES ('1514628159', false)
-- ON CONFLICT (mt5_account_id) DO NOTHING;
