import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

// GET all risk matrix entries
export async function GET() {
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("risk_matrix")
    .select("*")
    .order("symbol", { ascending: true });

  if (error) {
    console.error("Supabase error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data: data ?? [] });
}

// PUT update a risk matrix entry by symbol
export async function PUT(request: NextRequest) {
  const supabase = getSupabase();
  const body = await request.json();
  const { symbol, base_volume, sl_points, tp_points, be_trigger } = body;

  if (!symbol) {
    return NextResponse.json({ error: "Symbol is required" }, { status: 400 });
  }

  const updateData: Record<string, unknown> = {};
  if (base_volume !== undefined) updateData.base_volume = base_volume;
  if (sl_points !== undefined) updateData.sl_points = sl_points;
  if (tp_points !== undefined) updateData.tp_points = tp_points;
  if (be_trigger !== undefined) updateData.be_trigger = be_trigger;

  const { data, error } = await supabase
    .from("risk_matrix")
    .update(updateData)
    .eq("symbol", symbol)
    .select()
    .single();

  if (error) {
    console.error("Supabase update error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data });
}
