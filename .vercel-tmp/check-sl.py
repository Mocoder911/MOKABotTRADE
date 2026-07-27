from supabase import create_client
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

print('=== tactics_settings ===')
r = s.table('tactics_settings').select('key', 'value').execute()
for row in r.data:
    if 'stop' in row['key'].lower() or 'loss' in row['key'].lower() or 'sl' in row['key'].lower():
        print(f"  {row['key']}: {row['value']}")

print('\n=== Equity_Stop_Loss_Pct ===')
r2 = s.table('tactics_settings').select('key', 'value').eq('key', 'Equity_Stop_Loss_Pct').execute()
if r2.data:
    print(f"  {r2.data[0]['key']}: {r2.data[0]['value']}")
else:
    print("  Not found")
