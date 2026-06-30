import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function GET(request: NextRequest) {
  const cookieStore = await cookies();
  
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll() {
          // We don't need to set cookies for GET requests
        },
      },
    }
  );

  // Get current user session
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Get user's profile to find their MT5 account ID
  const { data: profile } = await supabase
    .from("profiles")
    .select("mt5_account_id")
    .eq("id", user.id)
    .single();

  // Build query
  let query = supabase
    .from("trades")
    .select("*")
    .eq("status", "open")
    .order("open_time", { ascending: false });

  // Filter by user's MT5 account if they have one
  if (profile?.mt5_account_id) {
    query = query.eq("account_id", profile.mt5_account_id);
  }

  const { data, error } = await query;

  if (error) {
    console.error("Supabase error:", error.message);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ trades: data ?? [] });
}
