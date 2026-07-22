import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

export async function GET(request: NextRequest) {
  try {
    const userId = request.headers.get("x-user-id");
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

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
        todayNet: 0,
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
        balance: 0, equity: 0, pl: 0, margin: 0, positions: 0, todayNet: 0, trades: [],
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

    // Calculate today's net profit: trades opened OR closed today (since midnight UTC)
    // Resets automatically at 00:00 UTC each day
    const now = new Date();
    const today = new Date(now);
    today.setUTCHours(0, 0, 0, 0);
    const todayISO = today.toISOString();

    // 1. Realized profit from trades CLOSED today
    let closedQuery = supabase
      .from("trades")
      .select("live_pl, closed_at, ticket, symbol")
      .eq("status", "closed")
      .gte("closed_at", todayISO);

    if (profile.mt5_account_id) {
      closedQuery = closedQuery.eq("account_id", profile.mt5_account_id);
    }

    const { data: closedTradesToday } = await closedQuery;
    const closedProfitToday = closedTradesToday?.reduce((sum, t) => sum + (t.live_pl ?? 0), 0) ?? 0;

    // Today's net = realized profit from trades closed today only
    const todayNetProfit = closedProfitToday;

    // Debug: log what we counted
    console.log("[todayNet] now=", now.toISOString(), "today=", todayISO);
    console.log("[todayNet] closed count=", closedTradesToday?.length ?? 0, "profit=", closedProfitToday);
    console.log("[todayNet] total=", todayNetProfit);

    return NextResponse.json({
      balance,
      equity,
      pl: totalPL,
      margin: totalMargin,
      positions,
      todayNet: todayNetProfit,
      trades: openTrades,
    });
  } catch (err) {
    console.error("[Account Metrics] Error:", err);
    return NextResponse.json({
      balance: 0, equity: 0, pl: 0, margin: 0, positions: 0, todayNet: 0, trades: [],
      error: err instanceof Error ? err.message : "Unknown error",
    });
  }
}
