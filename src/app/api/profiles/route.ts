import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Direct admin client with hardcoded key (Vercel env vars are empty in production)
const supabaseAdmin = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// GET all profiles or bot_status
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const field = searchParams.get("field");
  const mt5AccountId = searchParams.get("mt5_account_id");

  // Return bot_status from bot_status table
  if (field === "bot_status") {
    let resolvedMt5Id = mt5AccountId;

    // If no mt5_account_id provided, look it up from profiles using user_id
    const userId = searchParams.get("user_id");
    if (!resolvedMt5Id && userId) {
      const { data: prof } = await supabaseAdmin
        .from("profiles")
        .select("mt5_account_id")
        .eq("id", userId)
        .maybeSingle();
      resolvedMt5Id = prof?.mt5_account_id ?? null;
    }

    if (!resolvedMt5Id) {
      return NextResponse.json({ bot_active: false });
    }

    const { data, error } = await supabaseAdmin
      .from("bot_status")
      .select("bot_active")
      .eq("mt5_account_id", resolvedMt5Id)
      .maybeSingle();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ bot_active: data?.bot_active ?? false });
  }

  // Default: return all profiles (using admin client to bypass RLS)
  const { data, error } = await supabaseAdmin
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
    const { data: authData, error: authError } = await supabaseAdmin.auth.admin.createUser({
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

    const { data: profileData2, error: profileError } = await supabaseAdmin
      .from("profiles")
      .insert(profileData)
      .select()
      .single();

    if (profileError) {
      console.error("Profile create error:", profileError.message);
      // Try to clean up the auth user if profile creation fails
      await supabaseAdmin.auth.admin.deleteUser(userId);
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
  const { id, role, status, bot_active, full_name, mt5_account_id, mt5_password, mt5_server, avatar_url } = body;

  if (!id) {
    return NextResponse.json({ error: "Profile ID is required" }, { status: 400 });
  }

  // Update profile fields in profiles table
  const profileUpdate: Record<string, unknown> = {};
  if (role !== undefined) profileUpdate.role = role;
  if (status !== undefined) profileUpdate.status = status;
  if (full_name !== undefined) profileUpdate.full_name = full_name;
  if (mt5_account_id !== undefined) profileUpdate.mt5_account_id = mt5_account_id;
  if (mt5_password !== undefined) profileUpdate.mt5_password = mt5_password;
  if (mt5_server !== undefined) profileUpdate.mt5_server = mt5_server;
  if (avatar_url !== undefined) profileUpdate.avatar_url = avatar_url;

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
      .maybeSingle();

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
