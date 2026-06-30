import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

// GET all strategies
export async function GET() {
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("strategies")
    .select("*")
    .order("priority", { ascending: false });

  if (error) {
    console.error("Supabase error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data: data ?? [] });
}

// POST create a new strategy
export async function POST(request: NextRequest) {
  const supabase = getSupabase();
  const body = await request.json();

  const { name, description, symbol, entry_rules, exit_rules, sizing_rules, filters, is_active, priority, dry_run } = body;

  if (!name || !symbol) {
    return NextResponse.json({ error: "Name and symbol are required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("strategies")
    .insert({
      name,
      description: description || null,
      symbol,
      entry_rules: entry_rules || {},
      exit_rules: exit_rules || {},
      sizing_rules: sizing_rules || {},
      filters: filters || {},
      is_active: is_active ?? false,
      priority: priority ?? 0,
      dry_run: dry_run ?? true,  // Default to dry_run=true for safety
    })
    .select()
    .single();

  if (error) {
    console.error("Create strategy error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data }, { status: 201 });
}

// PUT update a strategy
export async function PUT(request: NextRequest) {
  const supabase = getSupabase();
  const body = await request.json();
  const { id, ...updateData } = body;

  if (!id) {
    return NextResponse.json({ error: "Strategy ID is required" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("strategies")
    .update(updateData)
    .eq("id", id)
    .select()
    .single();

  if (error) {
    console.error("Update strategy error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ data });
}

// DELETE a strategy
export async function DELETE(request: NextRequest) {
  const supabase = getSupabase();
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json({ error: "Strategy ID is required" }, { status: 400 });
  }

  const { error } = await supabase
    .from("strategies")
    .delete()
    .eq("id", id);

  if (error) {
    console.error("Delete strategy error:", error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
