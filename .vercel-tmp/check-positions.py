import MetaTrader5 as mt5

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    exit()

positions = mt5.positions_get()
print(f"Total positions: {len(positions)}")
print()

if positions:
    total_profit = 0
    for p in positions:
        print(f"  {p.symbol} | {p.type} | {p.volume} lots | P/L: ${p.profit:.2f} | Ticket: {p.ticket}")
        total_profit += p.profit
    print()
    print(f"Total P/L: ${total_profit:.2f}")
else:
    print("No open positions")

mt5.shutdown()
