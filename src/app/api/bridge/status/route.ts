import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseAdmin = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// GET — Fetch bridge heartbeat status
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const mt5AccountId = searchParams.get("mt5_account_id");

  if (!mt5AccountId) {
    return NextResponse.json(
      { error: "mt5_account_id is required" },
      { status: 400 }
    );
  }

  const { data, error } = await supabaseAdmin
    .from("bridge_heartbeat")
    .select("*")
    .eq("mt5_account_id", mt5AccountId)
    .maybeSingle();

  if (error) {
    // Table might not exist yet — return offline status instead of 500
    console.warn("[bridge/status] Query error:", error.message);
    return NextResponse.json({
      status: "unknown",
      last_heartbeat: null,
      cycle_count: 0,
      uptime_since: null,
      is_alive: false,
    });
  }

  if (!data) {
    return NextResponse.json({
      status: "unknown",
      last_heartbeat: null,
      cycle_count: 0,
      uptime_since: null,
      is_alive: false,
    });
  }

  // Check if heartbeat is within 30 seconds
  const lastHeartbeat = new Date(data.last_heartbeat);
  const now = new Date();
  const secondsAgo = (now.getTime() - lastHeartbeat.getTime()) / 1000;
  const isAlive = secondsAgo < 30;

  return NextResponse.json({
    status: isAlive ? data.status : "offline",
    last_heartbeat: data.last_heartbeat,
    cycle_count: data.cycle_count,
    uptime_since: data.uptime_since,
    is_alive: isAlive,
    seconds_since_heartbeat: Math.round(secondsAgo),
  });
}
