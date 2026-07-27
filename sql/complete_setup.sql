-- ============================================================================
-- MOKABotTRADE - Complete Database Setup Script
-- Run this ONCE in Supabase SQL Editor after creating a new project
-- ============================================================================

-- ─── 1. PROFILES TABLE ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT DEFAULT '',
  role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended')),
  mt5_account_id TEXT,
  mt5_password TEXT,
  mt5_server TEXT,
  bot_active BOOLEAN DEFAULT false,
  verification_status TEXT DEFAULT 'PENDING' CHECK (verification_status IN ('PENDING', 'VALIDATED', 'INVALID_CREDENTIALS')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Disable RLS so the app can access profiles
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- ─── 2. BOT_STATUS TABLE ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_status (
  mt5_account_id TEXT PRIMARY KEY,
  bot_active BOOLEAN DEFAULT false,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE bot_status DISABLE ROW LEVEL SECURITY;

-- ─── 3. TRADES TABLE ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY,
  ticket TEXT UNIQUE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  mt5_account_id TEXT,
  symbol TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('BUY', 'SELL')),
  volume NUMERIC NOT NULL DEFAULT 0,
  entry NUMERIC NOT NULL DEFAULT 0,
  sl NUMERIC DEFAULT 0,
  tp NUMERIC DEFAULT 0,
  live_pl NUMERIC DEFAULT 0,
  margin NUMERIC DEFAULT 0,
  open_time TIMESTAMPTZ,
  close_time TIMESTAMPTZ,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE trades DISABLE ROW LEVEL SECURITY;

-- ─── 4. STRATEGIES TABLE ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS strategies (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  config JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE strategies DISABLE ROW LEVEL SECURITY;

-- ─── 5. RISK_MATRIX TABLE ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_matrix (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  risk_level TEXT DEFAULT 'medium',
  max_position_size NUMERIC DEFAULT 0,
  stop_loss_pct NUMERIC DEFAULT 0,
  take_profit_pct NUMERIC DEFAULT 0,
  config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE risk_matrix DISABLE ROW LEVEL SECURITY;

-- ─── 6. BRIDGE_LOGS TABLE ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_logs (
  id BIGSERIAL PRIMARY KEY,
  mt5_account_id TEXT NOT NULL,
  level TEXT DEFAULT 'INFO' CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE bridge_logs DISABLE ROW LEVEL SECURITY;

-- ─── 7. BRIDGE_STATUS TABLE ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_heartbeat (
  mt5_account_id TEXT PRIMARY KEY,
  status TEXT DEFAULT 'offline',
  last_heartbeat TIMESTAMPTZ,
  cycle_count INTEGER DEFAULT 0,
  uptime_since TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE bridge_heartbeat DISABLE ROW LEVEL SECURITY;

-- ─── 8. ACCOUNT_METRICS TABLE ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_metrics (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  mt5_account_id TEXT,
  balance NUMERIC DEFAULT 0,
  equity NUMERIC DEFAULT 0,
  margin NUMERIC DEFAULT 0,
  free_margin NUMERIC DEFAULT 0,
  profit NUMERIC DEFAULT 0,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE account_metrics DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- SAFE TRIGGER: Auto-create profile when new user signs up
-- This replaces the broken hooks - safe with EXCEPTION handler
-- ============================================================================

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();

-- Create safe trigger function
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
  -- If anything fails, still allow the user to be created
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- CLEANUP: Remove any broken hooks from supabase_functions
-- ============================================================================
DELETE FROM supabase_functions.hooks;

-- ============================================================================
-- DONE! Database is ready.
-- Now create the admin user from the Supabase Dashboard:
-- Authentication > Users > Add User > Create New User
-- Email: moss911.moss@gmail.com
-- Password: M0hadm1n
-- Auto Confirm: YES
-- Then run the admin setup SQL below
-- ============================================================================
