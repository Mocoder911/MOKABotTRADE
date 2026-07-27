from supabase import create_client
import json
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

print('=' * 50)
print('=== TACTICS SETTINGS ===')
print('=' * 50)
r = s.table('tactics_settings').select('key', 'value').execute()
for row in r.data:
    print(f"  {row['key']}: {row['value']}")

print()
print('=' * 50)
print('=== STRATEGIES ===')
print('=' * 50)
r2 = s.table('strategies').select('*').execute()
print(f"  Count: {len(r2.data)}")
for row in r2.data:
    print(f"  ID: {row.get('id')}")
    print(f"  Name: {row.get('name')}")
    print(f"  Symbol: {row.get('symbol')}")
    print(f"  Active: {row.get('is_active')}")
    print(f"  Dry Run: {row.get('dry_run')}")
    print(f"  Entry Rules: {json.dumps(row.get('entry_rules', {}), indent=4)}")
    print(f"  Exit Rules: {json.dumps(row.get('exit_rules', {}), indent=4)}")
    print(f"  Sizing Rules: {json.dumps(row.get('sizing_rules', {}), indent=4)}")

print()
print('=' * 50)
print('=== PROFILES ===')
print('=' * 50)
r3 = s.table('profiles').select('mt5_account_id', 'server', 'status').execute()
for row in r3.data:
    print(f"  {row['mt5_account_id']} | {row['server']} | {row['status']}")
