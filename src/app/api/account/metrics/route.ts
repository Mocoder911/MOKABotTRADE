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

    // Get user profile first (needed for mt5_account_id)
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

    // Calculate 24 hours ago for today's net (match MT5 History tab)
    const now = new Date();
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const todayISO = twentyFourHoursAgo.toISOString();

    // Run all 3 queries in parallel for faster response
    const [tradesResult, accountResult, closedResult] = await Promise.all([
      // 1. Open trades
      supabase
        .from("trades")
        .select("*")
        .eq("status", "open")
        .order("open_time", { ascending: false })
        .then(({ data, error }) => error ? { data: [], error } : { data: data ?? [], error: null }),
      // 2. Account balance
      supabase
        .from("account_balance")
        .select("balance, equity")
        .eq("user_id", userId)
        .maybeSingle(),
      // 3. Only CLOSED deals today (trades only, not open positions or balance changes)
      (() => {
        let q = supabase
          .from("trades")
          .select("live_pl, closed_at, ticket, symbol, status")
          .eq("status", "closed")  // Only closed trades
          .gte("closed_at", todayISO);
        if (profile.mt5_account_id) {
          q = q.eq("account_id", profile.mt5_account_id);
        }
        return q;
      })()
    ]);

    const { data: trades, error } = tradesResult;
    if (error) {
      console.error("[Account Metrics] Trades query error:", error.message);
    }
    const openTrades = trades ?? [];

    // Calculate metrics from trades
    const totalPL = openTrades.reduce((sum, t) => sum + (t.live_pl ?? t.livePL ?? 0), 0);
    const totalMargin = openTrades.reduce((sum, t) => sum + (t.margin ?? t.volume ?? 0), 0);
    const positions = openTrades.length;

    // Balance from account_balance table (synced by MT5 bridge)
    const { data: accountData } = accountResult;
    const balance = accountData?.balance ?? 0;
    // Calculate equity dynamically: balance + floating P/L (always in sync with live trades)
    const equity = balance + totalPL;

    // Today's net from closed trades
    const { data: closedTradesToday } = closedResult;
    const todayNetProfit = closedTradesToday?.reduce((sum, t) => sum + (t.live_pl ?? 0), 0) ?? 0;

    // Debug: log what we counted
    console.log("[todayNet] now=", now.toISOString(), "today=", todayISO);
    console.log("[todayNet] closed count=", closedTradesToday?.length ?? 0, "profit=", todayNetProfit);
    console.log("[todayNet] sample deals:", JSON.stringify(closedTradesToday?.slice(0, 3) ?? [], null, 2));
    console.log("[todayNet] total=", todayNetProfit);

    return NextResponse.json(
      {
        balance,
        equity,
        pl: totalPL,
        margin: totalMargin,
        positions,
        todayNet: todayNetProfit,
        trades: openTrades,
      },
      {
        headers: {
          "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
          Pragma: "no-cache",
          Expires: "0",
        },
      }
    );
  } catch (err) {
    console.error("[Account Metrics] Error:", err);
    return NextResponse.json({
      balance: 0, equity: 0, pl: 0, margin: 0, positions: 0, todayNet: 0, trades: [],
      error: err instanceof Error ? err.message : "Unknown error",
    });
  }
}
