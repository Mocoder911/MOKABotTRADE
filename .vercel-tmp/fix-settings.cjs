from supabase import create_client
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

print('All tactics_settings:')
r = s.table('tactics_settings').select('key', 'value').execute()
for row in r.data:
    print(f"  {row['key']}: {row['value']}")

print()
print('Strategy sizing_rules:')
r2 = s.table('strategies').select('name', 'sizing_rules').eq('id', 2).execute()
if r2.data:
    print(f"  {r2.data[0]['name']}: {r2.data[0]['sizing_rules']}")
