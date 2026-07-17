import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseAdmin = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// POST — Send a command to the bridge
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { command, mt5_account_id } = body;

    if (!command || !mt5_account_id) {
      return NextResponse.json(
        { error: "command and mt5_account_id are required" },
        { status: 400 }
      );
    }

    if (!["RESTART", "STOP", "STATUS"].includes(command)) {
      return NextResponse.json(
        { error: "Invalid command. Must be RESTART, STOP, or STATUS" },
        { status: 400 }
      );
    }

    const { data, error } = await supabaseAdmin
      .from("bridge_commands")
      .insert({
        mt5_account_id,
        command,
        status: "pending",
      })
      .select()
      .single();

    if (error) {
      console.warn("[bridge/commands] Insert error:", error.message);
      return NextResponse.json(
        { error: "Failed to send command. Bridge tables may not exist yet. Run create_bridge_tables.sql first." },
        { status: 500 }
      );
    }

    return NextResponse.json({ data, success: true });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
