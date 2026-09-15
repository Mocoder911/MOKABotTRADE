import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  process.env.SUPABASE_SERVICE_ROLE_KEY || "",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// GET — Fetch recent bridge logs
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const mt5AccountId = searchParams.get("mt5_account_id");
  const limit = parseInt(searchParams.get("limit") || "100", 10);
  const since = searchParams.get("since");

  if (!mt5AccountId) {
    return NextResponse.json(
      { error: "mt5_account_id is required" },
      { status: 400 }
    );
  }

  let query = supabaseAdmin
    .from("bridge_logs")
    .select("*")
    .eq("mt5_account_id", mt5AccountId)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (since) {
    query = query.gte("created_at", since);
  }

  const { data, error } = await query;

  if (error) {
    // Table might not exist yet — return empty instead of 500
    console.warn("[bridge/logs] Query error:", error.message);
    return NextResponse.json({ logs: [] });
  }

  // Return in chronological order (oldest first)
  return NextResponse.json({ logs: (data || []).reverse() });
}
