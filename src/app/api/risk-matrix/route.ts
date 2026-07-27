import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

// GET all risk matrix entries
export async function GET() {
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

// POST - Add new risk matrix entry
export async function POST(request: NextRequest) {
  const body = await request.json();
  const { symbol, base_volume, sl_points, tp_points, be_trigger } = body;

  if (!symbol) {
    return NextResponse.json({ error: "Symbol is required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("risk_matrix")
    .upsert({
      symbol,
      base_volume: base_volume ?? 0.01,
      sl_points: sl_points ?? 100,
      tp_points: tp_points ?? 200,
      be_trigger: be_trigger ?? 50
    }, { onConflict: "symbol" })
    .select()
    .single();

  if (error) {
    console.error("Supabase insert error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data }, { status: 201 });
}

// PUT update a risk matrix entry by symbol
export async function PUT(request: NextRequest) {
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

// DELETE a risk matrix entry by symbol
export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get("symbol");

  if (!symbol) {
    return NextResponse.json({ error: "Symbol is required" }, { status: 400 });
  }

  const { error } = await supabase
    .from("risk_matrix")
    .delete()
    .eq("symbol", symbol);

  if (error) {
    console.error("Supabase delete error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
