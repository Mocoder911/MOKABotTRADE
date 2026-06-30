import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function getSupabaseAdmin() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error("Missing Supabase environment variables");
  }

  return createClient(url, key, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

export async function GET(request: NextRequest) {
  try {
    const userId = request.headers.get("x-user-id");
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const supabase = getSupabaseAdmin();

    // Get user profile
    const { data: profile } = await supabase
      .from("profiles")
      .select("id, mt5_account_id, status")
      .eq("id", userId)
      .maybeSingle();

    if (!profile || profile.status !== "active") {
      return NextResponse.json({
        balance: 0,
        equity: 0,
        pl: 0,
        margin: 0,
        positions: 0,
        trades: [],
      });
    }

    // Fetch open trades for this user
    let tradesQuery = supabase
      .from("trades")
      .select("*")
      .eq("status", "open")
      .order("open_time", { ascending: false });

    if (profile.mt5_account_id) {
      tradesQuery = tradesQuery.eq("account_id", profile.mt5_account_id);
    }

    const { data: trades, error } = await tradesQuery;

    if (error) {
      console.error("[Account Metrics] Trades query error:", error.message);
      return NextResponse.json({
        balance: 0, equity: 0, pl: 0, margin: 0, positions: 0, trades: [],
      });
    }

    const openTrades = trades ?? [];

    // Calculate real metrics from trades
    const totalPL = openTrades.reduce((sum, t) => sum + (t.live_pl ?? t.livePL ?? 0), 0);
    const totalMargin = openTrades.reduce((sum, t) => sum + (t.margin ?? t.volume ?? 0), 0);
    const positions = openTrades.length;

    // Balance and equity from account table if available, otherwise derive
    const { data: accountData } = await supabase
      .from("account_balance")
      .select("balance, equity")
      .eq("user_id", userId)
      .maybeSingle();

    const balance = accountData?.balance ?? 0;
    const equity = accountData?.equity ?? balance + totalPL;

    return NextResponse.json({
      balance,
      equity,
      pl: totalPL,
      margin: totalMargin,
      positions,
      trades: openTrades,
    });
  } catch (err) {
    console.error("[Account Metrics] Error:", err);
    return NextResponse.json({
      balance: 0, equity: 0, pl: 0, margin: 0, positions: 0, trades: [],
      error: err instanceof Error ? err.message : "Unknown error",
    });
  }
}
