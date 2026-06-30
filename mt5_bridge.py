"""
MOKABotTRADE — MT5 ↔ Supabase Bridge
=====================================
"""

import MetaTrader5 as mt5
import time
import sys
from datetime import datetime
from supabase import create_client

# ─── Supabase Config (Hardcoded — Service Role Key) ────────────────────────────
SUPABASE_URL = "https://gonfmiqwothggojdmglf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvbmZtaXF3b3RoZ2dvamRtZ2xmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc2Nzk5NiwiZXhwIjoyMDk4MzQzOTk2fQ.MJ1T20lriV99v_uczf3n-D52ybqODBKGiXSjjW8tudI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Exness Account ────────────────────────────────────────────────────────────
LOGIN = 260904217
PASSWORD = "Kikokok3@"
SERVER = "Exness-MT5Trial15"

# ─── MT5 Connection ────────────────────────────────────────────────────────────
print("=" * 50)
print("  MOKABotTRADE — MT5 Bridge")
print("=" * 50)

if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
    print(f"[ERROR] فشل الاتصال بـ MT5: {mt5.last_error()}")
    sys.exit(1)

account_info = mt5.account_info()
if not account_info:
    print("[ERROR] فشل الحصول على معلومات الحساب")
    mt5.shutdown()
    sys.exit(1)

print(f"[OK] متصل بـ MT5")
print(f"     Account: {account_info.login}")
print(f"     Server:  {account_info.server}")
print(f"     Balance: ${account_info.balance:.2f}")
print(f"     Equity:  ${account_info.equity:.2f}")
print("=" * 50)

MT5_ACCOUNT_ID = str(account_info.login)


# ─── Get User ID ───────────────────────────────────────────────────────────────
def get_user_id():
    try:
        result = supabase.table("profiles") \
            .select("id") \
            .eq("mt5_account_id", MT5_ACCOUNT_ID) \
            .maybe_single() \
            .execute()
        if result.data:
            return result.data["id"]
        return None
    except Exception as e:
        print(f"[USER ID ERROR] {e}")
        return None


# ─── Sync Account Balance ─────────────────────────────────────────────────────
def sync_account_balance():
    info = mt5.account_info()
    if not info:
        return

    user_id = get_user_id()
    if not user_id:
        print(f"[WARN] No profile found for account {MT5_ACCOUNT_ID}")
        return

    payload = {
        "user_id": user_id,
        "balance": info.balance,
        "equity": info.equity,
        "updated_at": "now()",
    }

    try:
        supabase.table("account_balance").upsert(payload, on_conflict="user_id").execute()
        print(f"[BALANCE] ${info.balance:.2f} | Equity: ${info.equity:.2f}")
    except Exception as e:
        print(f"[BALANCE ERROR] {e}")


# ─── Sync Open Trades ─────────────────────────────────────────────────────────
def sync_trades():
    positions = mt5.positions_get()
    if positions is None:
        positions = []

    current_tickets = set()

    for pos in positions:
        ticket = str(pos.ticket)
        current_tickets.add(ticket)

        trade_data = {
            "ticket": ticket,
            "account_id": MT5_ACCOUNT_ID,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
            "volume": pos.volume,
            "entry": pos.price_open,
            "sl": pos.sl,
            "tp": pos.tp,
            "live_pl": pos.profit,
            "margin": pos.margin,
            "open_time": datetime.fromtimestamp(pos.time).isoformat(),
            "status": "open",
        }

        try:
            supabase.table("trades").upsert(trade_data, on_conflict="ticket").execute()
        except Exception as e:
            print(f"[TRADE ERROR] Ticket {ticket}: {e}")

    # Mark closed trades
    try:
        db_trades = supabase.table("trades") \
            .select("ticket") \
            .eq("account_id", MT5_ACCOUNT_ID) \
            .eq("status", "open") \
            .execute()

        if db_trades.data:
            for t in db_trades.data:
                if t["ticket"] not in current_tickets:
                    supabase.table("trades") \
                        .update({"status": "closed"}) \
                        .eq("ticket", t["ticket"]) \
                        .execute()
                    print(f"[CLOSED] Ticket {t['ticket']}")
    except Exception as e:
        print(f"[CLOSE CHECK ERROR] {e}")

    print(f"[TRADES] {len(positions)} open positions synced")


# ─── Check Bot Active Status ──────────────────────────────────────────────────
def get_bot_status():
    """فحص حالة البوت من قاعدة البيانات"""
    try:
        result = supabase.table("profiles") \
            .select("bot_active") \
            .eq("mt5_account_id", MT5_ACCOUNT_ID) \
            .maybe_single() \
            .execute()
        if result.data:
            return result.data.get("bot_active", False)
        return False
    except Exception as e:
        print(f"[BOT STATUS ERROR] {e}")
        return False


# ─── Execute Trading Commands (when bot is active) ────────────────────────────
def execute_trading_logic():
    """هنا يتم تنفيذ أوامر التداول الحقيقية لما البوت يكون فعال"""
    # TODO: Add your trading strategy here
    # Example: Check signals, place orders, modify SL/TP, etc.
    pass


# ─── Main Loop ─────────────────────────────────────────────────────────────────
print("\n[Bridge] Starting sync loop (every 10 seconds)...\n")
print("[INFO] Data sync is ALWAYS ON (balance, trades)")
print("[INFO] Bot toggle controls trade EXECUTION only\n")

cycle = 0
while True:
    try:
        cycle += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # ALWAYS sync data (so dashboard shows real numbers)
        print(f"--- Cycle {cycle} @ {timestamp} ---")
        sync_account_balance()
        sync_trades()
        
        # Check bot status for trading execution
        bot_active = get_bot_status()
        
        if bot_active:
            print(f"[BOT] ▶ RUNNING — Executing trading logic...")
            execute_trading_logic()  # Place/modify trades here
        else:
            print(f"[BOT] ⏸  STANDBY — Monitoring only (toggle OFF in dashboard)")
        
        print(f"--- Next sync in 10s ---\n")
        time.sleep(10)

    except KeyboardInterrupt:
        print("\n[Bridge] Stopping...")
        mt5.shutdown()
        print("[Bridge] Done.")
        break

    except Exception as e:
        print(f"[FATAL] {e}")
        time.sleep(5)
