from supabase import create_client
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

# Remove Equity Stop Loss by setting to null
s.table('tactics_settings').update({'value': {'value': None}}).eq('key', 'Equity_Stop_Loss_Pct').execute()

print('Updated Equity_Stop_Loss_Pct:')
r = s.table('tactics_settings').select('key', 'value').eq('key', 'Equity_Stop_Loss_Pct').execute()
if r.data:
    print(f"  {r.data[0]['key']}: {r.data[0]['value']}")
