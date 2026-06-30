import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Use service role key to bypass RLS for webhook updates
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

// ─── MT5 Credential Validation (Placeholder) ──────────────────────────────────
// TODO: Replace with actual MT5 API connection
async function checkWithMetaTraderAPI({
  accountId,
  password,
  server,
}: {
  accountId: string;
  password: string;
  server: string;
}): Promise<boolean> {
  // Simulate MT5 server validation
  // In production, this should connect to the actual MT5 server/API
  console.log(`Validating MT5 account: ${accountId} on server: ${server}`);
  
  // Basic validation checks
  if (!accountId || !password || !server) {
    return false;
  }

  // Placeholder: return true for now
  // Replace with actual MT5 validation logic
  return true;
}

// ─── POST Handler for Supabase Webhook ────────────────────────────────────────
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { record, type } = body;

    if (!record) {
      return NextResponse.json(
        { error: "No record found in payload" },
        { status: 400 }
      );
    }

    const { id, mt5_account_id, mt5_password, mt5_server } = record;

    console.log(`[Webhook] Processing ${type} event for profile: ${id}`);
    console.log(`[Webhook] MT5 Account: ${mt5_account_id}, Server: ${mt5_server}`);

    // Validate MT5 credentials
    const isValid = await checkWithMetaTraderAPI({
      accountId: mt5_account_id,
      password: mt5_password,
      server: mt5_server,
    });

    // Update profile with verification result
    const supabase = getSupabaseAdmin();
    const verificationStatus = isValid ? "VALIDATED" : "INVALID_CREDENTIALS";

    const { error } = await supabase
      .from("profiles")
      .update({
        verification_status: verificationStatus,
        bot_active: false, // Keep bot inactive until admin activates
      })
      .eq("id", id);

    if (error) {
      console.error("[Webhook] Failed to update profile:", error.message);
      return NextResponse.json(
        { error: error.message },
        { status: 500 }
      );
    }

    console.log(`[Webhook] Profile ${id} updated: ${verificationStatus}`);

    return NextResponse.json({
      success: true,
      profile_id: id,
      verification_status: verificationStatus,
    });
  } catch (error) {
    console.error("[Webhook] Error processing request:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

// ─── GET Handler for testing/debugging ────────────────────────────────────────
export async function GET() {
  return NextResponse.json({
    status: "ok",
    message: "MT5 validation webhook endpoint is active",
  });
}
