import MetaTrader5 as mt5
from supabase import create_client

# Check Supabase settings
s = create_client(
    "https://lakbvdmjtoarmxmzvynu.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"
)

print("=" * 60)
print("DATABASE SETTINGS (Supabase)")
print("=" * 60)
r = s.table('tactics_settings').select('key', 'value').execute()
for row in r.data:
    k = row['key']
    v = row['value']
    if isinstance(v, dict):
        v = v.get('value', v)
    print(f"  {k}: {v}")

print()
print("=" * 60)
print("STRATEGIES TABLE")
print("=" * 60)
r2 = s.table('strategies').select('*').execute()
print(f"  Count: {len(r2.data)} strategies")

# Check MT5 positions
if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    exit()

positions = mt5.positions_get()
print()
print("=" * 60)
print(f"OPEN POSITIONS: {len(positions)}")
print("=" * 60)

if positions:
    total_profit = 0
    symbols_with_positions = set()
    for p in positions:
        direction = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        print(f"  {p.symbol:10s} | {direction:4s} | {p.volume} lots | P/L: ${p.profit:>7.2f} | Ticket: {p.ticket}")
        total_profit += p.profit
        symbols_with_positions.add(p.symbol)
    print()
    print(f"  Total P/L: ${total_profit:.2f}")
    print()
    print(f"  Symbols with positions ({len(symbols_with_positions)}): {', '.join(sorted(symbols_with_positions))}")

# Check which symbols are available
all_symbols = mt5.symbols_get()
forex_symbols = []
if all_symbols:
    excluded = ['XAU', 'XAG', 'BTC', 'ETH', 'USOIL', 'UKOIL', 'US30', 'NAS100', 'SPX500']
    for sym in all_symbols:
        is_excluded = any(e in sym.name for e in excluded)
        if not is_excluded and sym.name.endswith(('USDr', 'r', '')) or sym.name in ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD']:
            if not is_excluded:
                forex_symbols.append(sym.name)

print()
print("=" * 60)
print(f"AVAILABLE FOREX SYMBOLS: {len(forex_symbols)}")
print("=" * 60)
for s_name in sorted(forex_symbols):
    status = "OPEN" if s_name in symbols_with_positions else "closed"
    print(f"  {s_name:15s} | {status}")

mt5.shutdown()
