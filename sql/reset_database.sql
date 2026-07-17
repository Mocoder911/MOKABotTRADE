-- ═══════════════════════════════════════════════════════════════════
-- MOKABotTRADE — COMPLETE DATABASE RESET
-- Run this ONCE in Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════════

-- ─── STEP 1: Drop ALL triggers and functions ─────────────────────
-- Remove every trigger that could interfere with auth
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_mt5_inserted ON profiles;
DROP TRIGGER IF EXISTS on_profile_inserted ON profiles;
DROP TRIGGER IF EXISTS on_profile_updated ON profiles;
DROP TRIGGER IF EXISTS on_user_created ON auth.users;

-- Drop ALL custom functions (safe to run even if they don't exist)
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_mt5_account() CASCADE;
DROP FUNCTION IF EXISTS public.handle_profile_insert() CASCADE;
DROP FUNCTION IF EXISTS public.handle_profile_update() CASCADE;

-- Verify no triggers remain
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';

-- ─── STEP 2: Drop and recreate profiles table ────────────────────
DROP TABLE IF EXISTS profiles CASCADE;

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  full_name TEXT DEFAULT '',
  role TEXT DEFAULT 'user',
  status TEXT DEFAULT 'pending',
  mt5_account_id TEXT,
  mt5_password TEXT,
  mt5_server TEXT,
  bot_active BOOLEAN DEFAULT false,
  verification_status TEXT DEFAULT 'PENDING',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Disable RLS so the app can read/write
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- ─── STEP 3: Create SAFE trigger (simple, no external calls) ─────
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

-- ─── STEP 4: Clean ALL existing data ─────────────────────────────
DELETE FROM profiles;
DELETE FROM auth.users;

-- ─── STEP 5: Create admin user ───────────────────────────────────
INSERT INTO auth.users (
  id, instance_id, email, encrypted_password, 
  email_confirmed_at, raw_user_meta_data, 
  aud, role, created_at, updated_at
)
VALUES (
  gen_random_uuid(),
  '00000000-0000-0000-0000-000000000000',
  'moss911.moss@gmail.com',
  crypt('Admin123456!', gen_salt('bf')),
  NOW(),
  '{"full_name": "Admin"}',
  'authenticated',
  'authenticated',
  NOW(),
  NOW()
);

-- Create admin profile
INSERT INTO profiles (id, email, full_name, role, status, bot_active, verification_status)
SELECT id, email, 'Admin', 'admin', 'active', true, 'VALIDATED'
FROM auth.users
WHERE email = 'moss911.moss@gmail.com';

-- ─── STEP 6: Verify everything ───────────────────────────────────
SELECT '=== ADMIN USER ===' as info;
SELECT u.id, u.email, p.role, p.status, p.verification_status
FROM auth.users u
LEFT JOIN profiles p ON u.id = p.id;

SELECT '=== PROFILES TABLE COLUMNS ===' as info;
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'profiles'
ORDER BY ordinal_position;

SELECT '=== TRIGGERS ===' as info;
SELECT trigger_name, event_object_table, action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public';
