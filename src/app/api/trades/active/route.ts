import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export async function GET() {
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("trades")
    .select("*")
    .eq("status", "open")
    .order("open_time", { ascending: false });

  if (error) {
    console.error("Supabase error:", error.message);
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ trades: data ?? [] });
}
