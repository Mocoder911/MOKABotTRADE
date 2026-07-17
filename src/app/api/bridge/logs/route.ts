import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseAdmin = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
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
