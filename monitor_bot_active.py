from supabase import create_client
import time

s = create_client(
    "https://gonfmiqwothggojdmglf.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvbmZtaXF3b3RoZ2dvamRtZ2xmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc2Nzk5NiwiZXhwIjoyMDk4MzQzOTk2fQ.MJ1T20lriV99v_uczf3n-D52ybqODBKGiXSjjW8tudI"
)

# Set to True in bot_status table
print("Setting bot_active=True in bot_status table...")
s.table("bot_status").upsert({"mt5_account_id": "260904217", "bot_active": True}, on_conflict="mt5_account_id").execute()

# Monitor for 20 seconds
for i in range(10):
    result = s.table("bot_status").select("bot_active").eq("mt5_account_id", "260904217").maybe_single().execute()
    print(f"[{i*2}s] bot_active = {result.data}")
    time.sleep(2)
