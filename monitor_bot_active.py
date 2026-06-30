from supabase import create_client
import time

s = create_client(
    "https://gonfmiqwothggojdmglf.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvbmZtaXF3b3RoZ2dvamRtZ2xmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc2Nzk5NiwiZXhwIjoyMDk4MzQzOTk2fQ.MJ1T20lriV99v_uczf3n-D52ybqODBKGiXSjjW8tudI"
)

# Set to True
print("Setting bot_active=True...")
s.table("profiles").update({"bot_active": True}).eq("mt5_account_id", "260904217").execute()

# Monitor for 30 seconds
for i in range(15):
    result = s.table("profiles").select("bot_active").eq("mt5_account_id", "260904217").execute()
    print(f"[{i*2}s] bot_active = {result.data}")
    time.sleep(2)
