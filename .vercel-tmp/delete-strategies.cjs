from supabase import create_client
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

print('Current strategies:')
r = s.table('strategies').select('id', 'name', 'symbol', 'is_active').execute()
for row in r.data:
    print(f"  ID={row['id']}: {row['name']} | {row['symbol']} | active={row['is_active']}")

# Delete all strategies
if r.data:
    ids = [row['id'] for row in r.data]
    s.table('strategies').delete().in_('id', ids).execute()
    print(f"\nDeleted {len(ids)} strategies: {ids}")

print('\nStrategies after deletion:')
r2 = s.table('strategies').select('id', 'name').execute()
print(f"  Count: {len(r2.data)}")
