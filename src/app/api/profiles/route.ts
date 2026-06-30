import { NextRequest, NextResponse } from "next/server";
import { getSupabase, getSupabaseAdmin } from "@/lib/supabase";

// GET all profiles
export async function GET() {
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) {
    console.error("Supabase error:", error.message);
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
  const supabase = getSupabase();
  const body = await request.json();
  const { id, role, status, bot_active } = body;

  if (!id) {
    return NextResponse.json({ error: "Profile ID is required" }, { status: 400 });
  }

  const updateData: Record<string, unknown> = {};
  if (role !== undefined) updateData.role = role;
  if (status !== undefined) updateData.status = status;
  if (bot_active !== undefined) updateData.bot_active = bot_active;

  const { data, error } = await supabase
    .from("profiles")
    .update(updateData)
    .eq("id", id)
    .select()
    .single();

  if (error) {
    console.error("Supabase update error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data });
}
