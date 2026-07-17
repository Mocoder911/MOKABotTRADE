"""
MOKABotTRADE — Grid EA Engine
==============================
Architecture: Multi-Symbol Grid Trading System
- Opens positions on ALL Forex pairs simultaneously
- Grid orders at fixed point intervals
- Basket profit closes all orders per symbol
- All parameters configurable from Supabase (grid_config table)
- Excludes: Commodities (XAU, XAG, Oil) and Crypto (BTC, ETH)
"""
import MetaTrader5 as mt5
import time
import sys
import json
import hashlib
import multiprocessing
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from supabase import create_client

# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
SUPABASE_URL = "https://lakbvdmjtoarmxmzvynu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ═══════════════════════════════════════════════════════════════════════════════
# MT5 CREDENTIALS — Loaded from Supabase profiles table
# ═══════════════════════════════════════════════════════════════════════════════

def load_credentials(target_account_id: str = None):
    """Load MT5 credentials from profiles table.
    If target_account_id is provided, load that specific account.
    Otherwise, load the first active profile."""
    try:
        query = supabase.table("profiles").select(
            "mt5_account_id, mt5_password, mt5_server"
        ).eq("status", "active").not_.is_("mt5_account_id", "null")

        if target_account_id:
            query = query.eq("mt5_account_id", target_account_id)

        result = query.limit(1).execute()

        if result.data and result.data[0].get('mt5_account_id'):
            profile = result.data[0]
            return (
                int(profile['mt5_account_id']),
                profile['mt5_password'],
                profile.get('mt5_server', 'Exness-MT5Real')
            )
    except Exception as e:
        print(f"[CONFIG ERROR] {e}")

    # Fallback defaults — supports both accounts
    ACCOUNTS = {
        "474202217": (474202217, "Kikokok3@", "Exness-MT5Trial15"),
        "256711835": (256711835, "Kikokok3@", "Exness-MT5Real35"),
    }
    if target_account_id and target_account_id in ACCOUNTS:
        return ACCOUNTS[target_account_id]
    # Default to first account
    return (474202217, "Kikokok3@", "Exness-MT5Trial15")


# Accept optional account ID from command line: python mt5_bridge.py 474194522
_target = sys.argv[1] if len(sys.argv) > 1 else None
LOGIN, PASSWORD, SERVER = load_credentials(_target)
print(f"[CONFIG] Loaded: Account {LOGIN} on {SERVER}")

# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL WHITELIST — Forex ONLY (22 pairs, suffix: m)
# ═══════════════════════════════════════════════════════════════════════════════
ALLOWED_SYMBOLS = {
    "EURUSDm", "GBPUSDm", "USDJPYm", "USDCADm", "AUDUSDm", "NZDUSDm",
    "USDCHFm", "EURJPYm", "GBPJPYm", "CADJPYm", "AUDJPYm", "NZDJPYm",
    "CHFJPYm", "EURCADm", "GBPCADm", "EURAUDm", "GBPAUDm", "EURCHFm",
    "GBPCHFm", "CADCHFm",
}

# Explicitly excluded (crypto, metals, indices — never trade these)
EXCLUDED_PREFIXES = ("BTC", "ETH", "XAU", "XAG", "US5", "UK1")


def is_forex_pair(symbol: str) -> bool:
    """Return True only if symbol is in the strict Forex whitelist (exact match, case-sensitive)."""
    return symbol in ALLOWED_SYMBOLS


def is_excluded_symbol(symbol: str) -> bool:
    """Return True if symbol is crypto/metal/index that must NOT be traded."""
    upper = symbol.upper()
    for prefix in EXCLUDED_PREFIXES:
        if upper.startswith(prefix):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAGIC NUMBER GENERATOR — Deterministic per (account, symbol)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_magic_number(account_id: str, symbol: str) -> int:
    """Generate a unique magic number for each (account, symbol) pair."""
    key = f"{account_id}_{symbol}"
    return 100000 + int(hashlib.md5(key.encode()).hexdigest()[:6], 16) % 900000


# ═══════════════════════════════════════════════════════════════════════════════
# GRID ENGINE — Core logic
# ═══════════════════════════════════════════════════════════════════════════════
class GridEngine:
    """
    Grid EA Engine — manages grid trading across all Forex pairs.

    DB-driven configuration (grid_config table):
      - lot_size:      Position size per order (default 0.07)
      - grid_step:     Distance between grid orders in points (default 500)
      - max_orders:    Maximum orders per symbol (default 10)
      - basket_profit: Target profit ($) to close entire basket (default 20.0)
    """

    def __init__(self):
        self._config: Optional[Dict] = None
        self._config_time: float = 0
        self._basket_counter: Dict[str, int] = {}  # Track basket cycles per symbol
        self._volume_blacklist: set = set()  # Symbols that failed with Invalid volume

    # ─── Configuration ─────────────────────────────────────────────────────
    def fetch_config(self, mt5_account_id: str, force: bool = False) -> Dict:
        """Fetch grid config from DB. Cached for 30 seconds."""
        now = time.time()
        if not force and self._config and now - self._config_time < 30:
            return self._config

        try:
            result = supabase.table("grid_config").select("*").eq(
                "mt5_account_id", mt5_account_id
            ).maybe_single().execute()

            if result.data:
                self._config = result.data
                self._config_time = now
                return self._config
        except Exception as e:
            print(f"[GRID CONFIG] Error: {e}")

        # Fallback defaults
        self._config = {
            "lot_size": 0.07,
            "grid_step": 500,
            "max_orders": 10,
            "basket_profit": 20.0,
        }
        return self._config

    # ─── Symbol Management ─────────────────────────────────────────────────
    def get_allowed_symbols(self) -> List[str]:
        """Get all available Forex symbols from MT5 (auto-select all)."""
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return []

        allowed = []
        for s in all_symbols:
            if is_forex_pair(s.name):
                # Select symbol in Market Watch if not already visible
                if not s.visible:
                    if not mt5.symbol_select(s.name, True):
                        continue
                else:
                    # Ensure it stays selected
                    mt5.symbol_select(s.name, True)
                allowed.append(s.name)

        return allowed

    # ─── Grid Logic Per Symbol ─────────────────────────────────────────────
    def manage_grid(self, symbol: str, config: Dict, magic: int) -> None:
        """
        Manage grid for a single symbol with direction lock:
        1. Scan for conflicting positions (BUY+SELL) → STOP trading this symbol
        2. If no positions → open initial BUY order
        3. If basket profit >= target → close all (basket closed)
        4. If price moved grid_step → add grid order in SAME direction only
        """
        # Skip if symbol is blacklisted for invalid volume
        if symbol in self._volume_blacklist:
            print(f"[GRID] {symbol} — Skipped (volume blacklist)")
            return

        lot_size = config.get("lot_size", 0.07)
        grid_step = config.get("grid_step", 500)
        max_orders = config.get("max_orders", 10)
        basket_profit = config.get("basket_profit", 20.0)

        # Get all positions for this symbol with our magic number
        positions = mt5.positions_get(symbol=symbol)
        all_pos_count = len(positions) if positions else 0
        my_positions = [p for p in (positions or []) if p.magic == magic]

        # Debug: show what we see
        if all_pos_count > 0:
            print(f"[GRID] {symbol} — {all_pos_count} total positions, {len(my_positions)} with our magic ({magic})")

        # ── SAFETY: Detect conflicting positions (BUY + Sell on same symbol) ──
        if my_positions:
            buy_count = sum(1 for p in my_positions if p.type == mt5.POSITION_TYPE_BUY)
            sell_count = sum(1 for p in my_positions if p.type == mt5.POSITION_TYPE_SELL)
            if buy_count > 0 and sell_count > 0:
                print(f"[CONFLICT] {symbol} — Has {buy_count} BUY + {sell_count} SELL positions! STOPPED. Manual intervention required.")
                return  # Do NOT trade this symbol until conflict is resolved

        # ── No positions: Open initial BUY order ──
        if not my_positions:
            self._basket_counter[symbol] = self._basket_counter.get(symbol, 0) + 1
            basket_num = self._basket_counter[symbol]
            print(f"[GRID] {symbol} — No positions. Opening initial BUY order (basket #{basket_num})")
            self._open_order(symbol, "BUY", lot_size, magic)
            return

        # ── Determine grid direction from first position ──
        first_pos = min(my_positions, key=lambda p: p.time)
        grid_direction = "BUY" if first_pos.type == mt5.POSITION_TYPE_BUY else "SELL"

        # ── Calculate basket profit ──
        total_profit = sum(p.profit + p.swap + getattr(p, 'commission', 0.0) for p in my_positions)

        # ── Basket profit reached → Close all ──
        if total_profit >= basket_profit:
            print(f"[GRID] {symbol} — Basket profit ${total_profit:.2f} >= ${basket_profit:.2f} → Closing {len(my_positions)} orders")
            self._close_all(my_positions)
            return

        # ── Check if we should add a grid order ──
        if len(my_positions) >= max_orders:
            return  # Max orders reached

        # Find the last (most recent) position price
        last_pos = max(my_positions, key=lambda p: p.time)
        last_price = last_pos.price_open

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return

        info = mt5.symbol_info(symbol)
        if not info or info.point == 0:
            return

        current_price = tick.ask

        # Calculate grid distance in points
        distance_points = abs(current_price - last_price) / info.point

        if distance_points >= grid_step:
            # Only add grid order in the SAME direction as existing positions
            if grid_direction == "BUY":
                if current_price < last_price:
                    print(f"[GRID] {symbol} — Adding BUY grid order #{len(my_positions) + 1} @ {current_price:.5f} (distance: {distance_points:.0f} pts)")
                    self._open_order(symbol, "BUY", lot_size, magic)
            else:  # SELL direction
                if current_price > last_price:
                    print(f"[GRID] {symbol} — Adding SELL grid order #{len(my_positions) + 1} @ {current_price:.5f} (distance: {distance_points:.0f} pts)")
                    self._open_order(symbol, "SELL", lot_size, magic)

    # ─── Volume Validation ─────────────────────────────────────────────────
    def _validate_volume(self, symbol: str, requested_volume: float) -> float:
        """Validate and adjust lot size based on symbol's volume constraints."""
        info = mt5.symbol_info(symbol)
        if not info:
            return requested_volume

        vol_min = getattr(info, 'volume_min', 0.01) or 0.01
        vol_max = getattr(info, 'volume_max', 100.0) or 100.0
        vol_step = getattr(info, 'volume_step', 0.01) or 0.01

        # Crypto special handling: default to 0.01 if requested volume is too high
        if symbol in ("BTCUSDm", "ETHUSDm") and requested_volume > vol_max:
            requested_volume = 0.01

        # Clamp to min/max
        volume = max(vol_min, min(requested_volume, vol_max))

        # Round to nearest step
        if vol_step > 0:
            volume = round(round(volume / vol_step) * vol_step, 2)

        # Final safety: ensure within bounds after rounding
        volume = max(vol_min, min(volume, vol_max))

        return volume

    # ─── Order Execution ───────────────────────────────────────────────────
    def _open_order(self, symbol: str, order_type: str, volume: float, magic: int) -> bool:
        """Open a raw market order — NO SL/TP (basket profit only). Checks free margin and volume constraints."""
        # ── Free margin safety check ──
        account_info = mt5.account_info()
        if not account_info:
            return False
        if account_info.margin_free < (volume * 100):  # Rough check: ~$100 needed for 0.07 lot
            print(f"[MARGIN] {symbol} — Insufficient free margin (${account_info.margin_free:.2f}). Skipping.")
            return False

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return False

        info = mt5.symbol_info(symbol)
        if not info:
            return False

        # ── Volume validation ──
        volume = self._validate_volume(symbol, volume)

        price = tick.ask if order_type == "BUY" else tick.bid
        order_side = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_side,
            "price": price,
            "sl": 0.0,
            "tp": 0.0,
            "deviation": 20,
            "magic": magic,
            "comment": "MOKA_GRID",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTE] {order_type} {symbol} @ {price} | Vol: {volume} | Ticket: {result.order}")
            return True
        elif result and result.retcode == mt5.TRADE_RETCODE_NO_MONEY:
            print(f"[MARGIN] {symbol} — Not enough money to open {volume} lot. Skipping.")
            return False
        elif result and result.retcode == mt5.TRADE_RETCODE_INVALID_VOLUME:
            print(f"[VOLUME ERROR] {symbol} — Invalid volume {volume}. Blacklisting for this cycle.")
            self._volume_blacklist.add(symbol)
            return False
        else:
            error = result.comment if result else "No result"
            print(f"[EXECUTE FAILED] {order_type} {symbol}: {error}")
            return False

    def _close_all(self, positions: list) -> None:
        """Close all positions in the basket."""
        for pos in positions:
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                continue

            close_price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": close_price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": "MOKA_GRID_CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[CLOSE] {pos.symbol} ticket {pos.ticket} | P/L: ${pos.profit:.2f}")
            else:
                error = result.comment if result else "No result"
                print(f"[CLOSE FAILED] {pos.symbol} ticket {pos.ticket}: {error}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SYNC — Balance, Trades, Bot Status
# ═══════════════════════════════════════════════════════════════════════════════
def get_user_id(mt5_account_id: str) -> Optional[str]:
    try:
        result = supabase.table("profiles").select("id").eq(
            "mt5_account_id", mt5_account_id).maybe_single().execute()
        return result.data["id"] if result.data else None
    except Exception:
        return None


def sync_account_balance(mt5_account_id: str):
    info = mt5.account_info()
    if not info:
        print("  [BALANCE ERROR] Could not get account info")
        return
    user_id = get_user_id(mt5_account_id)
    if not user_id:
        print(f"  [BALANCE ERROR] No user found for account {mt5_account_id}")
        return
    try:
        supabase.table("account_balance").upsert({
            "user_id": user_id,
            "balance": info.balance,
            "equity": info.equity,
            "updated_at": "now()",
        }, on_conflict="user_id").execute()
        print(f"  [BALANCE] Synced: balance=${info.balance:.2f} equity=${info.equity:.2f}")
    except Exception as e:
        print(f"  [BALANCE ERROR] {e}")


def sync_trades(mt5_account_id: str):
    """Sync all open positions to Supabase trades table."""
    positions = mt5.positions_get() or []
    current_tickets = set()

    for pos in positions:
        ticket = str(pos.ticket)
        current_tickets.add(ticket)
        try:
            margin = getattr(pos, 'margin', 0.0) or 0.0
            live_pl = pos.profit
            supabase.table("trades").upsert({
                "ticket": ticket,
                "account_id": mt5_account_id,
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": pos.volume,
                "entry": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "live_pl": live_pl,
                "margin": margin,
                "open_time": datetime.fromtimestamp(pos.time).isoformat(),
                "status": "open",
            }, on_conflict="ticket").execute()
        except Exception as e:
            print(f"  [SYNC ERROR] Ticket {ticket}: {e}")

    # Mark closed trades
    try:
        db_trades = supabase.table("trades").select("ticket").eq(
            "account_id", mt5_account_id).eq("status", "open").execute()
        if db_trades.data:
            closed_count = 0
            for t in db_trades.data:
                if t["ticket"] not in current_tickets:
                    supabase.table("trades").update({"status": "closed"}).eq(
                        "ticket", t["ticket"]).execute()
                    closed_count += 1
            if closed_count > 0:
                print(f"  [SYNC] Marked {closed_count} trades as closed")
    except Exception as e:
        print(f"  [SYNC ERROR] Close check: {e}")


def cleanup_excluded_positions():
    """Close all open positions on excluded symbols (crypto, metals, indices)."""
    positions = mt5.positions_get() or []
    closed = 0
    for pos in positions:
        if is_excluded_symbol(pos.symbol):
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                continue
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "position": pos.ticket,
                "sl": 0.0,
                "tp": 0.0,
                "deviation": 20,
                "magic": pos.magic,
                "comment": "EXCLUDED_CLEANUP",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"  [CLEANUP] Closed {pos.symbol} ticket {pos.ticket} (excluded symbol)")
                closed += 1
            else:
                error = result.comment if result else "No result"
                print(f"  [CLEANUP FAILED] {pos.symbol}: {error}")
    if closed > 0:
        print(f"  [CLEANUP] Closed {closed} positions on excluded symbols")


def get_bot_status(mt5_account_id: str) -> bool:
    """Read bot_active from the bot_status table."""
    try:
        result = supabase.table("bot_status").select("bot_active").eq(
            "mt5_account_id", mt5_account_id).maybe_single().execute()
        if result.data:
            return result.data.get("bot_active", False)
        return False
    except Exception as e:
        print(f"[WARN] get_bot_status error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE CONTROL — Logging, Heartbeat, Commands
# ═══════════════════════════════════════════════════════════════════════════════
BRIDGE_START_TIME = None


def bridge_log(level: str, message: str, mt5_account_id: str = None):
    """Write log to DB and print to terminal."""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{level}] {message}")
    if not mt5_account_id:
        return
    try:
        supabase.table("bridge_logs").insert({
            "mt5_account_id": mt5_account_id,
            "level": level,
            "message": message,
        }).execute()
    except Exception as e:
        print(f"  [DB ERROR] Log write failed: {e}")


def send_heartbeat(mt5_account_id: str, cycle_count: int, status: str = "running"):
    """Update heartbeat in bridge_heartbeat table."""
    try:
        supabase.table("bridge_heartbeat").upsert({
            "mt5_account_id": mt5_account_id,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "cycle_count": cycle_count,
            "uptime_since": BRIDGE_START_TIME,
        }, on_conflict="mt5_account_id").execute()
    except Exception as e:
        print(f"  [DB ERROR] Heartbeat failed: {e}")


def check_commands(mt5_account_id: str) -> Optional[str]:
    """Check for pending commands from the dashboard."""
    try:
        result = supabase.table("bridge_commands").select("*") \
            .eq("mt5_account_id", mt5_account_id) \
            .eq("status", "pending") \
            .order("created_at", desc=False) \
            .limit(1).execute()
        if result.data:
            cmd = result.data[0]
            supabase.table("bridge_commands").update(
                {"status": "executed", "executed_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", cmd["id"]).execute()
            return cmd["command"]
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE ACCOUNT RUNNER — Runs Grid EA for one account
# ═══════════════════════════════════════════════════════════════════════════════
def run_account(login: int, password: str, server: str):
    """Run the Grid EA for a single MT5 account. Designed to run in its own process."""
    global LOGIN, PASSWORD, SERVER, MT5_ACCOUNT_ID, BRIDGE_START_TIME

    LOGIN = login
    PASSWORD = password
    SERVER = server

    print(f"\n{'=' * 70}")
    print(f"  [{login}] Starting Grid EA Engine")
    print(f"{'=' * 70}")

    # Connect to MT5
    if not mt5.initialize(login=login, password=password, server=server):
        print(f"[{login}] [ERROR] MT5 connection failed: {mt5.last_error()}")
        return

    account_info = mt5.account_info()
    if not account_info:
        print(f"[{login}] [ERROR] Failed to get account info")
        mt5.shutdown()
        return

    print(f"[{login}] [OK] Connected | Balance: ${account_info.balance:.2f}")

    MT5_ACCOUNT_ID = str(login)
    BRIDGE_START_TIME = datetime.now(timezone.utc).isoformat()
    engine = GridEngine()

    bridge_log("INFO", "Grid EA Bridge started", MT5_ACCOUNT_ID)

    cycle = 0
    while True:
        try:
            cycle += 1
            ts = datetime.now().strftime('%H:%M:%S')

            # Check for commands from dashboard
            cmd = check_commands(MT5_ACCOUNT_ID)
            if cmd == "STOP":
                bridge_log("WARN", "STOP command received from dashboard", MT5_ACCOUNT_ID)
                send_heartbeat(MT5_ACCOUNT_ID, cycle, status="stopped")
                print(f"[{login}] [BRIDGE] Stopped via dashboard command")
                mt5.shutdown()
                break
            elif cmd == "RESTART":
                bridge_log("INFO", "RESTART command received — re-initializing", MT5_ACCOUNT_ID)
                mt5.shutdown()
                if not mt5.initialize(login=login, password=password, server=server):
                    bridge_log("ERROR", f"MT5 re-init failed: {mt5.last_error()}", MT5_ACCOUNT_ID)
                    time.sleep(5)
                    continue
                engine = GridEngine()
                bridge_log("INFO", "MT5 re-initialized successfully", MT5_ACCOUNT_ID)
                BRIDGE_START_TIME = datetime.now(timezone.utc).isoformat()

            # Sync data
            sync_account_balance(MT5_ACCOUNT_ID)
            sync_trades(MT5_ACCOUNT_ID)

            # Clean up positions on excluded symbols (crypto, metals, indices)
            cleanup_excluded_positions()

            # Check bot status
            bot_active = get_bot_status(MT5_ACCOUNT_ID)

            if bot_active:
                config = engine.fetch_config(MT5_ACCOUNT_ID)
                allowed_symbols = engine.get_allowed_symbols()

                print(f"[{login}] --- Cycle {cycle} @ {ts} | {len(allowed_symbols)} Forex pairs ---")
                print(f"[{login}]   Config: Lot={config['lot_size']} | Step={config['grid_step']}pts | "
                      f"Max={config['max_orders']} | Basket=${config['basket_profit']}")

                for symbol in allowed_symbols:
                    magic = generate_magic_number(MT5_ACCOUNT_ID, symbol)
                    engine.manage_grid(symbol, config, magic)
            else:
                print(f"[{login}] --- Cycle {cycle} @ {ts} --- [ENGINE] Bot inactive, skipping")

            send_heartbeat(MT5_ACCOUNT_ID, cycle)
            time.sleep(10)

        except KeyboardInterrupt:
            bridge_log("INFO", "Bridge stopped by user", MT5_ACCOUNT_ID)
            send_heartbeat(MT5_ACCOUNT_ID, cycle, status="stopped")
            mt5.shutdown()
            break

        except Exception as e:
            bridge_log("ERROR", f"Cycle error: {e}", MT5_ACCOUNT_ID)
            print(f"[{login}] [FATAL] {e}")
            time.sleep(5)


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-ACCOUNT FETCH — Read all active accounts from Supabase
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_all_accounts() -> List[Dict]:
    """Fetch all active MT5 accounts from Supabase + fallback accounts."""
    accounts = []
    seen_logins = set()

    # 1. From Supabase profiles table
    try:
        result = supabase.table("profiles").select(
            "mt5_account_id, mt5_password, mt5_server"
        ).eq("status", "active").not_.is_("mt5_account_id", "null").not_.is_("mt5_password", "null").execute()

        for p in (result.data or []):
            aid = p.get('mt5_account_id')
            pwd = p.get('mt5_password')
            srv = p.get('mt5_server', 'Exness-MT5Real')
            if aid and pwd:
                login = int(aid)
                if login not in seen_logins:
                    accounts.append({'login': login, 'password': pwd, 'server': srv})
                    seen_logins.add(login)
    except Exception as e:
        print(f"[CONFIG ERROR] Failed to fetch accounts from DB: {e}")

    # 2. Fallback hardcoded accounts (always available)
    FALLBACK_ACCOUNTS = [
        {"login": 474202217, "password": "Kikokok3@", "server": "Exness-MT5Trial15"},
        {"login": 256711835, "password": "Kikokok3@", "server": "Exness-MT5Real35"},
    ]
    for acc in FALLBACK_ACCOUNTS:
        if acc['login'] not in seen_logins:
            accounts.append(acc)
            seen_logins.add(acc['login'])

    return accounts


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-ACCOUNT LAUNCHER — Spawn one process per account
# ═══════════════════════════════════════════════════════════════════════════════
def run_all_accounts():
    """Run all active accounts sequentially (MT5 limitation: one connection at a time)."""
    accounts = fetch_all_accounts()

    if not accounts:
        print("[ERROR] No active accounts found in database!")
        print("  Add accounts to the profiles table with status='active'")
        sys.exit(1)

    print(f"\n{'=' * 70}")
    print(f"  MOKABotTRADE — Sequential Multi-Account Grid EA Engine")
    print(f"  Found {len(accounts)} active account(s)")
    print(f"{'=' * 70}")

    for acc in accounts:
        print(f"  [{acc['login']}] Server: {acc['server']}")
    print()

    cycle = 0
    while True:
        try:
            cycle += 1
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"\n{'=' * 70}")
            print(f"  Cycle {cycle} @ {ts} — Processing {len(accounts)} accounts sequentially")
            print(f"{'=' * 70}")

            for acc in accounts:
                login = acc['login']
                account_id = str(login)
                
                # Check bot status BEFORE connecting
                bot_active = get_bot_status(account_id)
                if not bot_active:
                    print(f"\n--- [{login}] Bot inactive, skipping (no connection) ---")
                    continue
                
                print(f"\n--- [{login}] Connecting to {acc['server']} ---")

                # Connect to MT5
                if not mt5.initialize(login=login, password=acc['password'], server=acc['server']):
                    error = mt5.last_error()
                    print(f"[{login}] [ERROR] MT5 connection failed: {error}")
                    mt5.shutdown()
                    continue

                account_info = mt5.account_info()
                if not account_info:
                    print(f"[{login}] [ERROR] Failed to get account info")
                    mt5.shutdown()
                    continue

                print(f"[{login}] [OK] Balance: ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f}")

                # Sync data
                sync_account_balance(account_id)
                sync_trades(account_id)
                cleanup_excluded_positions()

                # Trade
                engine = GridEngine()
                config = engine.fetch_config(account_id)
                allowed_symbols = engine.get_allowed_symbols()

                print(f"[{login}] Trading: {len(allowed_symbols)} pairs | Lot={config['lot_size']} | Basket=${config['basket_profit']}")

                for symbol in allowed_symbols:
                    try:
                        magic = generate_magic_number(account_id, symbol)
                        engine.manage_grid(symbol, config, magic)
                    except Exception as e:
                        print(f"[{login}] [ERROR] {symbol}: {e}")

                send_heartbeat(account_id, cycle)
                mt5.shutdown()
                print(f"[{login}] Done. Disconnecting.")

            print(f"\n[LAUNCHER] Cycle {cycle} complete. Waiting 30s...\n")
            time.sleep(30)

        except KeyboardInterrupt:
            print("\n[LAUNCHER] Stopped by user (Ctrl+C)")
            mt5.shutdown()
            break
        except Exception as e:
            print(f"[LAUNCHER] Cycle error: {e}")
            try:
                mt5.shutdown()
            except:
                pass
            time.sleep(10)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single account mode: python mt5_bridge.py <account_id>
        target_id = sys.argv[1]
        creds = load_credentials(target_id)
        run_account(creds[0], creds[1], creds[2])
    else:
        # Multi-account mode: python mt5_bridge.py
        run_all_accounts()
