import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseAdmin = createClient(
  "https://lakbvdmjtoarmxmzvynu.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE",
  { auth: { autoRefreshToken: false, persistSession: false } }
);

export async function POST(request: NextRequest) {
  console.log("=== SIGNUP API START ===");
  
  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  
  console.log("RECEIVED PAYLOAD:", JSON.stringify(body, null, 2));

  const { email, password, full_name, mt5_account_id, mt5_password, mt5_server } = body;

  // Validation
  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
  }

  if (password.length < 6) {
    return NextResponse.json({ error: "Password must be at least 6 characters" }, { status: 400 });
  }

  if (!mt5_account_id || !mt5_password || !mt5_server) {
    return NextResponse.json({ error: "MT5 Account ID, Password, and Server are required" }, { status: 400 });
  }

  try {
    console.log("[Signup] Creating auth user:", email);
    
    const { data: authData, error: authError } = await supabaseAdmin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: { 
        full_name: full_name || "", 
        mt5_account_id,
        mt5_password,
        mt5_server
      }
    });

    console.log("[Signup] createUser result:", { 
      userId: authData?.user?.id, 
      error: authError ? JSON.stringify(authError) : null 
    });

    if (authError) {
      const errMsg = authError.message || "";
      if (errMsg.includes("already") || errMsg.includes("exists") || errMsg.includes("registered")) {
        return NextResponse.json({ error: "This email is already registered." }, { status: 400 });
      }
      return NextResponse.json({ error: errMsg || "Failed to create user" }, { status: 400 });
    }

    if (!authData?.user) {
      return NextResponse.json({ error: "Failed to create user" }, { status: 500 });
    }

    const userId = authData.user.id;
    console.log("[Signup] Auth user created:", userId);

    // Update profile with full MT5 data (trigger already created basic profile)
    const { error: profileError } = await supabaseAdmin
      .from("profiles")
      .update({
        full_name: full_name || "",
        mt5_account_id,
        mt5_password,
        mt5_server,
        verification_status: "PENDING"
      })
      .eq("id", userId);

    if (profileError) {
      console.error("[Signup] Profile update error:", profileError.message);
    } else {
      console.log("[Signup] Profile updated with mt5_server:", mt5_server);
    }

    return NextResponse.json({ 
      success: true, 
      user_id: userId,
      message: "Account created. Pending admin approval." 
    });

  } catch (err) {
    console.error("[Signup] EXCEPTION:", err);
    return NextResponse.json({ 
      error: err instanceof Error ? err.message : "Unknown error" 
    }, { status: 500 });
  }
}
