import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Admin Supabase client using service role key (bypasses RLS)
function getSupabaseAdmin() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  );
}

export async function GET(request: NextRequest) {
  // Get user ID from header (sent by client)
  const userId = request.headers.get("x-user-id");

  if (!userId) {
    return NextResponse.json({ error: "Unauthorized: No user ID provided" }, { status: 401 });
  }

  const supabase = getSupabaseAdmin();

  // Get user's profile to find their MT5 account ID
  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("id, mt5_account_id, role, status")
    .eq("id", userId)
    .single();

  if (profileError || !profile) {
    console.error("Profile fetch error:", profileError?.message);
    return NextResponse.json({ error: "Profile not found" }, { status: 404 });
  }

  // Only active users can fetch trades
  if (profile.status !== "active") {
    return NextResponse.json({ error: "Account not active" }, { status: 403 });
  }

  // Build query
  let query = supabase
    .from("trades")
    .select("*")
    .eq("status", "open")
    .order("open_time", { ascending: false });

  // Filter by user's MT5 account if they have one
  if (profile.mt5_account_id) {
    query = query.eq("account_id", profile.mt5_account_id);
  }

  const { data, error } = await query;

  if (error) {
    console.error("Supabase error:", error.message);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ trades: data ?? [] });
}
