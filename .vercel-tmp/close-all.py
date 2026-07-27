import MetaTrader5 as mt5

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
    exit()

positions = mt5.positions_get()
print(f"Closing {len(positions)} positions...")
print()

closed = 0
failed = 0

for p in positions:
    # Determine close order type (opposite of position type)
    if p.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(p.symbol).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(p.symbol).ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": order_type,
        "position": p.ticket,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "close all",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  ✓ {p.symbol} closed | Ticket: {p.ticket}")
        closed += 1
    else:
        print(f"  ✗ {p.symbol} FAILED | Error: {result.comment if result else 'Unknown'}")
        failed += 1

print()
print(f"Closed: {closed} | Failed: {failed}")

mt5.shutdown()
