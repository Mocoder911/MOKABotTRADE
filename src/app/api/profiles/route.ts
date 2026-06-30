import { NextRequest, NextResponse } from "next/server";
import { getSupabase, getSupabaseAdmin } from "@/lib/supabase";
import { createClient } from "@supabase/supabase-js";

// Direct admin client with hardcoded key (same as Python bridge)
const supabaseAdmin = createClient(
  "https://gonfmiqwothggojdmglf.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvbmZtaXF3b3RoZ2dvamRtZ2xmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc2Nzk5NiwiZXhwIjoyMDk4MzQzOTk2fQ.MJ1T20lriV99v_uczf3n-D52ybqODBKGiXSjjW8tudI",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// GET all profiles or bot_status
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const field = searchParams.get("field");
  const mt5AccountId = searchParams.get("mt5_account_id");

  // Return bot_status from bot_status table
  if (field === "bot_status" && mt5AccountId) {
    const { data, error } = await supabaseAdmin
      .from("bot_status")
      .select("bot_active")
      .eq("mt5_account_id", mt5AccountId)
      .maybeSingle();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ bot_active: data?.bot_active ?? false });
  }

  // Default: return all profiles
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data: data ?? [] });
}

// POST — Admin creates a new user (requires Service Role Key)
export async function POST(request: NextRequest) {
  try {
    const supabase = getSupabaseAdmin(); // Use admin client for auth.admin operations
    const body = await request.json();

    const {
      email,
      password,
      full_name,
      role = "user",
      status = "active",
      mt5_account_id,
      mt5_password,
      mt5_server,
    } = body;

    // Validation
    if (!email || !password || !full_name) {
      return NextResponse.json(
        { error: "Email, password, and full name are required" },
        { status: 400 }
      );
    }

    // 1. Create user in Supabase Auth
    const { data: authData, error: authError } = await supabase.auth.admin.createUser({
      email,
      password,
      email_confirm: true, // Auto-confirm email
    });

    if (authError) {
      console.error("Auth create user error:", authError.message);
      return NextResponse.json({ error: authError.message }, { status: 500 });
    }

    if (!authData.user) {
      return NextResponse.json({ error: "Failed to create user" }, { status: 500 });
    }

    const userId = authData.user.id;

    // 2. Create profile with MT5 data
    const profileData: Record<string, unknown> = {
      id: userId,
      email,
      full_name,
      role,
      status,
    };

    if (mt5_account_id) profileData.mt5_account_id = mt5_account_id;
    if (mt5_password) profileData.mt5_password = mt5_password;
    if (mt5_server) profileData.mt5_server = mt5_server;

    const { data: profileData2, error: profileError } = await supabase
      .from("profiles")
      .insert(profileData)
      .select()
      .single();

    if (profileError) {
      console.error("Profile create error:", profileError.message);
      // Try to clean up the auth user if profile creation fails
      await supabase.auth.admin.deleteUser(userId);
      return NextResponse.json({ error: profileError.message }, { status: 500 });
    }

    return NextResponse.json({ data: profileData2 }, { status: 201 });
  } catch (err) {
    console.error("Create user error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}

// PUT update a profile
export async function PUT(request: NextRequest) {
  const body = await request.json();
  const { id, role, status, bot_active } = body;

  if (!id) {
    return NextResponse.json({ error: "Profile ID is required" }, { status: 400 });
  }

  // Update profile fields (role, status) in profiles table
  const profileUpdate: Record<string, unknown> = {};
  if (role !== undefined) profileUpdate.role = role;
  if (status !== undefined) profileUpdate.status = status;

  if (Object.keys(profileUpdate).length > 0) {
    const { data, error } = await supabaseAdmin
      .from("profiles")
      .update(profileUpdate)
      .eq("id", id)
      .select()
      .single();

    if (error) {
      console.error("[API PUT] profiles update error:", error.message);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
  }

  // Update bot_active in bot_status table (separate table to avoid profiles trigger issues)
  if (bot_active !== undefined) {
    // Look up mt5_account_id from profile
    const { data: profile } = await supabaseAdmin
      .from("profiles")
      .select("mt5_account_id")
      .eq("id", id)
      .single();

    if (!profile?.mt5_account_id) {
      return NextResponse.json({ error: "No mt5_account_id found for this profile" }, { status: 400 });
    }

    const { data, error } = await supabaseAdmin
      .from("bot_status")
      .upsert({ mt5_account_id: profile.mt5_account_id, bot_active, updated_at: new Date().toISOString() }, { onConflict: "mt5_account_id" })
      .select()
      .single();

    if (error) {
      console.error("[API PUT] bot_status update error:", error.message);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ data });
  }

  return NextResponse.json({ success: true });
}
