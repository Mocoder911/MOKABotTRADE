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

    const period = request.nextUrl.searchParams.get("period") || "daily";
    const startParam = request.nextUrl.searchParams.get("start");
    const endParam = request.nextUrl.searchParams.get("end");

    // Get user profile
    const { data: profile } = await supabase
      .from("profiles")
      .select("id, mt5_account_id, status")
      .eq("id", userId)
      .maybeSingle();

    if (!profile || profile.status !== "active") {
      return NextResponse.json({
        trades: [],
        totalProfit: 0,
        tradeCount: 0,
        balance: 0,
        period,
      });
    }

    // Calculate date range based on period
    const now = new Date();
    let startDate: Date;
    let endDate: Date = now;

    switch (period) {
      case "daily":
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        break;
      case "weekly":
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case "monthly":
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case "custom":
        if (startParam && endParam) {
          startDate = new Date(startParam);
          endDate = new Date(endParam);
          endDate.setHours(23, 59, 59, 999); // End of the end date
        } else {
          startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        }
        break;
      case "all-time":
      default:
        startDate = new Date(2020, 0, 1); // From beginning
        break;
    }

    // Query winning trades (live_pl > 0) closed within the date range
    let tradesQuery = supabase
      .from("trades")
      .select("symbol, live_pl, close_time, type, volume")
      .eq("user_id", userId)
      .eq("status", "closed")
      .gt("live_pl", 0)
      .gte("close_time", startDate.toISOString())
      .lte("close_time", endDate.toISOString())
      .order("close_time", { ascending: false });

    if (profile.mt5_account_id) {
      tradesQuery = tradesQuery.eq("account_id", profile.mt5_account_id);
    }

    const { data: trades, error } = await tradesQuery;

    if (error) {
      console.error("[Reports] Trades query error:", error.message);
      return NextResponse.json({
        trades: [],
        totalProfit: 0,
        tradeCount: 0,
        balance: 0,
        period,
        error: error.message,
      });
    }

    const winningTrades = trades ?? [];
    const totalProfit = winningTrades.reduce((sum, t) => sum + (t.live_pl ?? 0), 0);

    // Get current balance
    const { data: accountData } = await supabase
      .from("account_balance")
      .select("balance")
      .eq("user_id", userId)
      .maybeSingle();

    const balance = accountData?.balance ?? 0;

    return NextResponse.json(
      {
        trades: winningTrades,
        totalProfit: Math.round(totalProfit * 100) / 100,
        tradeCount: winningTrades.length,
        balance,
        period,
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
    console.error("[Reports] Error:", err);
    return NextResponse.json(
      {
        trades: [],
        totalProfit: 0,
        tradeCount: 0,
        balance: 0,
        period: "daily",
        error: err instanceof Error ? err.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
