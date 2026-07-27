import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Hardcoded admin client (Vercel env vars are empty in production)
const supabase = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

export async function GET(request: NextRequest) {
  try {
    // Get user ID from header (sent by client)
    const userId = request.headers.get("x-user-id");

    if (!userId) {
      return NextResponse.json({ error: "Unauthorized: No user ID provided" }, { status: 401 });
    }

    // Get user's profile to find their MT5 account ID
    const { data: profile, error: profileError } = await supabase
      .from("profiles")
      .select("id, mt5_account_id, role, status")
      .eq("id", userId)
      .maybeSingle(); // Use maybeSingle instead of single to handle null gracefully

    if (profileError) {
      console.error("[Trades API] Profile fetch error:", profileError.message);
    }

    // If no profile found, return empty trades (user might be pending)
    if (!profile) {
      console.log(`[Trades API] No profile found for user ${userId}, returning empty trades`);
      return NextResponse.json({ trades: [] });
    }

    // If user is not active, return empty trades
    if (profile.status !== "active") {
      console.log(`[Trades API] User ${userId} is ${profile.status}, returning empty trades`);
      return NextResponse.json({ trades: [] });
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
      console.error("[Trades API] Supabase query error:", error.message);
      return NextResponse.json(
        { error: error.message, trades: [] },
        { status: 500 }
      );
    }

    return NextResponse.json({ trades: data ?? [] });
  } catch (err) {
    console.error("[Trades API] Unexpected error:", err);
    // Return empty trades instead of crashing
    return NextResponse.json({ 
      trades: [], 
      error: err instanceof Error ? err.message : "Unknown error" 
    });
  }
}
