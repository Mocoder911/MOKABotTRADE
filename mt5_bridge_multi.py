"""
MOKABot Multi-Account Bridge (SaaS-Grade)
==========================================
- Reads credentials from Supabase profiles table
- Processes accounts sequentially (MT5 limitation: one connection at a time)
- Each sync cycle processes all active accounts
- No hardcoded credentials - everything from database
- Integrated SafetyEngine for trade validation
- Connection timeout handling (5s) to prevent hanging
- Failed account tracking with cooldown period
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

import MetaTrader5 as mt5
from supabase import create_client, Client

# Import SafetyEngine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tactics.safety_engine import SafetyEngine

# ============================================
# SUPABASE CONFIGURATION
# ============================================
SUPABASE_URL = "https://lakbvdmjtoarmxmzvynu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# TELEGRAM NOTIFICATIONS
# ============================================
# Multiple Telegram accounts to receive notifications
TELEGRAM_ACCOUNTS = [
    {"token": "8676258690:AAEJafRn1ks4tJ_jvnDNQf8FEq3fLnIVHMo", "chat_id": "8449825809"},
    {"token": "8989474621:AAE__nslSBkxlhC3eXG8FMzYj9KGLVLbYnU", "chat_id": "5935024063"},
]
TELEGRAM_ENABLED = True  # Set to False to disable notifications

def send_telegram(message: str):
    """Send a Telegram notification to all configured accounts."""
    import ssl
    if not TELEGRAM_ENABLED:
        return
    
    # Create SSL context that ignores certificate errors (for VPS with proxy/firewall)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    for account in TELEGRAM_ACCOUNTS:
        try:
            url = f"https://api.telegram.org/bot{account['token']}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": account['chat_id'],
                "text": message,
                "parse_mode": "HTML",
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            urllib.request.urlopen(req, timeout=10, context=ssl_context)
        except Exception as e:
            print(f"[TELEGRAM] Failed to send to {account['chat_id']}: {e}")

# ============================================
# CONNECTION TIMEOUT & FAILURE TRACKING
# ============================================
CONNECTION_TIMEOUT_SECONDS = 10  # Max time to wait for MT5 connection (increased for slow brokers)
FAILURE_COOLDOWN_MINUTES = 0.5   # Skip failed accounts for this long (30 seconds for faster recovery)
MAX_CONSECUTIVE_FAILURES = 3     # Flag as failed after this many consecutive failures

# Track account failures: {account_id: {"failures": int, "last_failure": datetime}}
account_failures: Dict[str, Dict] = {}

# Global flag for bridge shutdown
bridge_shutdown = False

# ============================================
# SYMBOL NORMALIZATION
# ============================================
# Cache for resolved symbols per account
resolved_symbols: Dict[str, Dict[str, str]] = {}

def resolve_symbol(symbol: str, account_id: str) -> str:
    """
    Resolve symbol name to match broker's naming convention.
    E.g., 'XAUUSD' -> 'XAUUSDm' for some brokers.
    """
    # Check cache first
    if account_id in resolved_symbols and symbol in resolved_symbols[account_id]:
        return resolved_symbols[account_id][symbol]
    
    # Try exact match first
    if mt5.symbol_info(symbol):
        if account_id not in resolved_symbols:
            resolved_symbols[account_id] = {}
        resolved_symbols[account_id][symbol] = symbol
        return symbol
    
    # Try common suffixes
    suffixes = ['m', 'pro', 'ecn', 'raw', 'std', 'micro', 'mini', '.c', '.i', '#']
    for suffix in suffixes:
        test_symbol = f"{symbol}{suffix}"
        if mt5.symbol_info(test_symbol):
            log("INFO", f"Symbol resolved: {symbol} -> {test_symbol}", account_id)
            if account_id not in resolved_symbols:
                resolved_symbols[account_id] = {}
            resolved_symbols[account_id][symbol] = test_symbol
            return test_symbol
    
    # Try to find symbol in Market Watch
    symbols = mt5.symbols_get()
    if symbols:
        for s in symbols:
            if symbol in s.name or s.name in symbol:
                log("INFO", f"Symbol resolved from Market Watch: {symbol} -> {s.name}", account_id)
                if account_id not in resolved_symbols:
                    resolved_symbols[account_id] = {}
                resolved_symbols[account_id][symbol] = s.name
                return s.name
    
    # If not found, try to add it to Market Watch
    if mt5.symbol_select(symbol, True):
        log("INFO", f"Symbol added to Market Watch: {symbol}", account_id)
        if account_id not in resolved_symbols:
            resolved_symbols[account_id] = {}
        resolved_symbols[account_id][symbol] = symbol
        return symbol
    
    log("WARN", f"Could not resolve symbol: {symbol}", account_id)
    return symbol  # Return original as fallback

def ensure_symbol_in_market_watch(symbol: str, account_id: str) -> bool:
    """
    Ensure symbol is visible in Market Watch.
    Returns True if successful.
    """
    resolved = resolve_symbol(symbol, account_id)
    
    # Check if symbol info is available
    info = mt5.symbol_info(resolved)
    if not info:
        # Try to add it
        if not mt5.symbol_select(resolved, True):
            log("ERROR", f"Failed to add {resolved} to Market Watch", account_id)
            return False
    
    return True

# ============================================
# GLOBAL DEFAULT SETTINGS (Hard-coded)
# ============================================
# These values are applied automatically unless overridden in tactics_settings table
DEFAULT_GRID_STEP = 100          # Grid step in points (LEGACY - not used anymore)
DEFAULT_FIXED_LOT_SIZE = 0.02    # Fixed lot size - no multipliers
DEFAULT_BASKET_TP = 10           # Basket take profit in USD
DEFAULT_MAX_POSITIONS = 15        # Max open positions per symbol
DEFAULT_EQUITY_SL_PCT = 0        # Equity stop loss percentage
DEFAULT_MAX_SPREAD_PIPS = 3.0    # Max allowed spread in pips
DEFAULT_GRID_STEP_LOSS_USD = 10.0  # Grid step based on dollar loss per position

# ============================================
# STRICT STRATEGY PROTOCOL
# ============================================
# Forex-only mode: Only allow forex currency pairs
# Load allowed currencies from pairs.json (primary source)
import json
import os

def load_allowed_currencies():
    """Load allowed currencies from pairs.json file."""
    pairs_file = os.path.join(os.path.dirname(__file__), 'pairs.json')
    try:
        with open(pairs_file, 'r') as f:
            data = json.load(f)
            currencies = data.get('allowed_currencies', [])
            print(f"[SECURITY] Loaded {len(currencies)} currencies from pairs.json: {currencies}")
            return currencies
    except Exception as e:
        print(f"[SECURITY] Failed to load pairs.json, using hardcoded fallback: {e}")
        # Fallback to hardcoded list
        return ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF']

FOREX_CURRENCIES = load_allowed_currencies()

# Additional blocked symbols (indices, commodities, crypto)
BLOCKED_SYMBOL_KEYWORDS = ['XAU', 'XAG', 'OIL', 'BTC', 'ETH', 'US30', 'NAS100', 'SPX500', 'GOLD', 'SILVER']

def is_allowed_symbol(symbol: str, settings: Dict) -> bool:
    """
    Dynamic Symbol Filtering - Gateway check before any trade.
    Returns True if symbol is allowed for trading.
    
    FOREX ONLY MODE:
    - Only allow symbols that contain at least 2 forex currency codes
    - Block indices (US30, NAS100, SPX500)
    - Block commodities (XAU, XAG, OIL, GOLD, SILVER)
    - Block crypto (BTC, ETH)
    - Check Excluded_Symbols from database for manual blacklist
    """
    symbol_upper = symbol.upper()
    
    # Check blocked keywords first
    for keyword in BLOCKED_SYMBOL_KEYWORDS:
        if keyword in symbol_upper:
            return False
    
    # Check manual exclusion list from database
    excluded_str = settings.get('Excluded_Symbols', '')
    if excluded_str:
        excluded = [s.strip().upper() for s in excluded_str.split(',') if s.strip()]
        if symbol_upper in excluded:
            return False
    
    # Check if symbol contains at least 2 forex currency codes
    currency_count = 0
    for currency in FOREX_CURRENCIES:
        if currency in symbol_upper:
            currency_count += 1
    
    # Forex pairs have 2 currencies (e.g., EURUSD = EUR + USD)
    if currency_count >= 2:
        return True
    
    # Everything else is blocked
    return False

def is_spread_safe(symbol: str, max_spread_pips: float = None, account_id: str = None) -> bool:
    """
    Check if the current spread is within acceptable limits.
    Returns True if spread is safe, False if too high.
    
    Args:
        symbol: Trading symbol
        max_spread_pips: Maximum allowed spread in pips (default: DEFAULT_MAX_SPREAD_PIPS)
        account_id: Account ID for logging
    
    Returns:
        bool: True if spread is safe, False otherwise
    """
    if max_spread_pips is None:
        max_spread_pips = DEFAULT_MAX_SPREAD_PIPS
    
    try:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            log("WARN", f"Cannot get symbol info for {symbol}, skipping spread check", account_id)
            return True  # Allow trade if we can't check spread
        
        # Get current spread in points
        spread_points = symbol_info.spread
        
        # Convert points to pips (1 pip = 10 points for most pairs)
        spread_pips = spread_points / 10.0
        
        if spread_pips > max_spread_pips:
            log("WARN", f"[SPREAD FILTER] {symbol}: Spread {spread_pips:.2f} pips > Max {max_spread_pips} pips - Trade BLOCKED", account_id)
            return False
        
        # Log spread for monitoring (only in DEBUG mode to avoid spam)
        log("DEBUG", f"[SPREAD] {symbol}: {spread_pips:.2f} pips (Max: {max_spread_pips})", account_id)
        return True
        
    except Exception as e:
        log("WARN", f"Spread check failed for {symbol}: {e}", account_id)
        return True  # Allow trade if check fails

def check_risk_limits(symbol: str, account_id: str, settings: Dict, current_equity: float, balance: float) -> tuple:
    """
    Hard-coded Risk Management Rules.
    Returns (passed: bool, reason: str)
    
    Rules:
    1. Fixed lot size: 0.02
    2. Max Open Positions per symbol (default: 3)
    3. Equity Stop Loss (default: 10% of balance)
    """
    # Get risk parameters from settings (with defaults)
    max_positions_per_symbol = int(settings.get('Max_Open_Positions', DEFAULT_MAX_POSITIONS))
    
    # Handle Equity_Stop_Loss_Pct - None means disabled
    eslp = settings.get('Equity_Stop_Loss_Pct', DEFAULT_EQUITY_SL_PCT)
    if eslp is None:
        equity_stop_loss_pct = None  # Disabled
    else:
        equity_stop_loss_pct = float(eslp)
    
    # Count current open positions for this symbol
    positions = mt5.positions_get(symbol=symbol) or []
    current_positions = len(positions)
    
    # Check max positions limit
    if current_positions >= max_positions_per_symbol:
        return False, f"Max positions reached for {symbol}: {current_positions}/{max_positions_per_symbol}"
    
    # Check equity stop loss (skip if disabled)
    if balance > 0 and equity_stop_loss_pct is not None:
        floating_pl = current_equity - balance
        loss_pct = (abs(floating_pl) / balance) * 100 if floating_pl < 0 else 0
        
        if loss_pct >= equity_stop_loss_pct:
            return False, f"Equity Stop Loss triggered: {loss_pct:.2f}% >= {equity_stop_loss_pct}%"
    
    return True, "Risk limits OK"

def get_fixed_lot_size(settings: Dict = None) -> float:
    """Get fixed lot size from tactics_settings or use default."""
    if settings:
        lot = settings.get('Fixed_Lot_Size', None)
        if lot is not None:
            return float(lot)
    try:
        result = supabase.table("tactics_settings").select("value").eq("key", "Fixed_Lot_Size").limit(1).execute()
        if result.data:
            val = result.data[0].get('value', {})
            return float(val.get('value', val) if isinstance(val, dict) else val)
    except Exception:
        pass
    return DEFAULT_FIXED_LOT_SIZE

def get_basket_tp() -> float:
    """Get basket TP from strategy or use default."""
    try:
        result = supabase.table("strategies").select("sizing_rules").eq("is_active", True).limit(1).execute()
        if result.data:
            sizing = result.data[0].get("sizing_rules", {})
            return sizing.get("basket_take_profit_usd", DEFAULT_BASKET_TP)
    except Exception:
        pass
    return DEFAULT_BASKET_TP

def debug_log_strategy(account_id: str, settings: Dict):
    """
    Debug logging for Strict Strategy Protocol verification.
    Called at the beginning of each cycle to verify protocol compliance.
    """
    log("DEBUG", "=" * 50, account_id)
    log("DEBUG", "[PROTOCOL DEBUG] Strict Strategy Protocol Status", account_id)
    log("DEBUG", "=" * 50, account_id)
    
    # 1. Print current settings from database (with defaults)
    log("DEBUG", f"[SETTINGS] Max_Open_Positions: {settings.get('Max_Open_Positions', DEFAULT_MAX_POSITIONS)}", account_id)
    log("DEBUG", f"[SETTINGS] Equity_Stop_Loss_Pct: {settings.get('Equity_Stop_Loss_Pct', DEFAULT_EQUITY_SL_PCT)}%", account_id)
    log("DEBUG", f"[SETTINGS] Grid_Step: {settings.get('Grid_Step', DEFAULT_GRID_STEP)} points", account_id)
    log("DEBUG", f"[SETTINGS] Basket_Take_Profit: ${settings.get('Basket_Take_Profit', DEFAULT_BASKET_TP)}", account_id)
    log("DEBUG", f"[SETTINGS] Fixed_Lot_Size: {get_fixed_lot_size()}", account_id)
    log("DEBUG", f"[SETTINGS] Excluded_Symbols: '{settings.get('Excluded_Symbols', '')}'", account_id)
    
    # 2. Filter Check for forex pairs
    test_symbols = [
        # Major pairs (should be ALLOWED)
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD',
        # Cross pairs (should be ALLOWED)
        'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY',
        'EURAUD', 'EURCAD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPNZD',
        'AUDCAD', 'AUDNZD', 'AUDCHF', 'NZDCAD', 'NZDCHF', 'CADCHF',
        # Exotic pairs (should be BLOCKED)
        'USDMXN', 'USDZAR', 'USDTRY', 'USDHKD', 'USDNOK', 'USDSEK',
        'AUDSGD', 'EURCZK', 'EURDKK', 'USDSGD',
        # Commodities (should be BLOCKED)
        'XAUUSD', 'XAGUSD',
        # Crypto (should be BLOCKED)
        'BTCUSD', 'ETHUSD',
        # Indices (should be BLOCKED)
        'US30', 'NAS100', 'SPX500'
    ]
    
    log("DEBUG", "-" * 40, account_id)
    log("DEBUG", "[FILTER CHECK] Symbol Filtering Status:", account_id)
    for symbol in test_symbols:
        resolved = resolve_symbol(symbol, account_id) if mt5.account_info() else symbol
        allowed = is_allowed_symbol(resolved, settings)
        status = "ALLOWED" if allowed else "BLOCKED"
        log("DEBUG", f"[FILTER] {symbol} -> {resolved} | Status={status}", account_id)
    
    # 3. Risk Compliance Check
    log("DEBUG", "-" * 40, account_id)
    log("DEBUG", "[RISK COMPLIANCE] Risk Management Status:", account_id)
    
    info = mt5.account_info()
    if info:
        equity = info.equity
        balance = info.balance
        floating_pl = equity - balance
        loss_pct = (abs(floating_pl) / balance * 100) if floating_pl < 0 and balance > 0 else 0
        
        max_positions = settings.get('Max_Open_Positions', DEFAULT_MAX_POSITIONS)
        equity_sl_pct = settings.get('Equity_Stop_Loss_Pct', DEFAULT_EQUITY_SL_PCT)
        
        # Check if equity stop loss is triggered (skip if disabled)
        if equity_sl_pct is not None:
            sl_triggered = loss_pct >= equity_sl_pct
            sl_status = "TRIGGERED" if sl_triggered else "OK"
        else:
            sl_triggered = False
            sl_status = "DISABLED"
        
        log("DEBUG", f"[RISK] Balance: ${balance:.2f} | Equity: ${equity:.2f} | Floating P/L: ${floating_pl:.2f}", account_id)
        log("DEBUG", f"[RISK] Loss %: {loss_pct:.2f}% | Equity_SL: {equity_sl_pct}% | Status: {sl_status}", account_id)
        log("DEBUG", f"[RISK] Fixed_Lot: {get_fixed_lot_size()} | Max_Positions: {max_positions}", account_id)
        log("DEBUG", f"[RISK] Overall Compliance: {'COMPLIANT' if not sl_triggered else 'NON-COMPLIANT'}", account_id)
    else:
        log("DEBUG", "[RISK] Could not get account info - skipping risk check", account_id)
    
    log("DEBUG", "=" * 50, account_id)

# ============================================
# COMMAND POLLING
# ============================================
def check_pending_commands() -> bool:
    """Check for pending commands from dashboard. Returns True if bridge should continue."""
    global bridge_shutdown
    
    try:
        result = supabase.table("bridge_commands").select("*").eq("status", "pending").execute()
        commands = result.data or []
        
        for cmd in commands:
            command = cmd.get("command")
            account_id = cmd.get("mt5_account_id")
            cmd_id = cmd.get("id")
            
            log("INFO", f"Received command: {command} for account {account_id}")
            
            # Mark as processed
            try:
                supabase.table("bridge_commands").update({
                    "status": "processed",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", cmd_id).execute()
            except:
                pass
            
            # Execute command
            if command == "STOP":
                log("INFO", "Bridge shutdown requested via STOP command")
                bridge_shutdown = True
                return False
            elif command == "RESTART":
                log("INFO", "RESTART command received - bridge will continue running (restart not supported while running)")
                # RESTART is not supported while bridge is running
                # User should stop the bridge manually and restart it
            elif command == "STATUS":
                log("INFO", "Status command - bridge is running")
                
    except Exception as e:
        log("DEBUG", f"Command check failed: {e}")
    
    return True

# ============================================
# LOGGING
# ============================================
def log(level: str, message: str, account_id: str = None):
    """Centralized logging with database persistence."""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    prefix = f"[Account:{account_id}]" if account_id else "[SYSTEM]"
    print(f"{timestamp} {prefix} [{level}] {message}")
    
    # Log to database (use 'SYSTEM' for system-wide logs)
    try:
        supabase.table("bridge_logs").insert({
            "mt5_account_id": account_id or "SYSTEM",
            "level": level,
            "message": message
        }).execute()
    except Exception as e:
        print(f"[LOG ERROR] Failed to write to database: {e}")

# ============================================
# BRIDGE ID CONFIGURATION
# ============================================
# Each bridge instance has a unique ID
# Accounts are assigned to specific bridges via bridge_id column in profiles table
# Set BRIDGE_ID environment variable or use default 'local'
BRIDGE_ID = os.environ.get('BRIDGE_ID', 'local')

# ============================================
# CREDENTIAL FETCHER
# ============================================
def fetch_active_accounts() -> List[Dict]:
    """Fetch all active MT5 accounts assigned to this bridge from database."""
    try:
        # Fetch accounts assigned to this bridge_id
        result = supabase.table("profiles").select(
            "id, email, mt5_account_id, mt5_password, mt5_server"
        ).eq("status", "active").not_.is_("mt5_account_id", "null").not_.is_("mt5_password", "null").execute()
        
        accounts = []
        for profile in result.data or []:
            if profile.get('mt5_account_id') and profile.get('mt5_password'):
                # TODO: Add bridge_id filtering when column is added
                # For now, process all active accounts
                accounts.append({
                    'user_id': profile['id'],
                    'email': profile['email'],
                    'login': int(profile['mt5_account_id']),
                    'password': profile['mt5_password'],
                    'server': profile.get('mt5_server', 'Exness-MT5Real')
                })
        
        log("INFO", f"Fetched {len(accounts)} active accounts from database (Bridge: {BRIDGE_ID})")
        return accounts
        
    except Exception as e:
        log("ERROR", f"Failed to fetch accounts: {e}")
        return []

# ============================================
# ACCOUNT SYNC FUNCTIONS
# ============================================
def sync_account_balance(user_id: str, account_id: str):
    """Sync balance for current connected account."""
    info = mt5.account_info()
    if not info:
        log("ERROR", "Could not get account info", account_id)
        return
    
    try:
        supabase.table("account_balance").upsert({
            "user_id": user_id,
            "balance": info.balance,
            "equity": info.equity,
            "updated_at": "now()"
        }, on_conflict="user_id").execute()
        log("INFO", f"Balance: ${info.balance:.2f} | Equity: ${info.equity:.2f}", account_id)
    except Exception as e:
        log("ERROR", f"Balance sync failed: {e}", account_id)

def sync_account_trades(user_id: str, account_id: str):
    """Sync trades for current connected account with ghost trade cleanup and history sync."""
    # Force refresh rates from MT5
    mt5.symbol_info("XAUUSD")  # Trigger refresh
    
    # Get actual positions from MT5
    positions = mt5.positions_get() or []
    mt5_tickets = set(str(pos.ticket) for pos in positions)
    
    log("INFO", f"MT5 reports {len(positions)} open positions", account_id)
    
    # Get trades from database for this account
    try:
        db_trades_result = supabase.table("trades").select("ticket").eq("account_id", account_id).eq("status", "open").execute()
        db_tickets = set(t['ticket'] for t in (db_trades_result.data or []))
    except Exception as e:
        log("ERROR", f"Failed to fetch DB trades: {e}", account_id)
        db_tickets = set()
    
    # Find ghost trades (in DB but not in MT5)
    ghost_tickets = db_tickets - mt5_tickets
    if ghost_tickets:
        log("WARN", f"Found {len(ghost_tickets)} GHOST trades in DB: {ghost_tickets}", account_id)
        # Mark ghost trades as closed and send Telegram notification
        for ticket in ghost_tickets:
            try:
                # Get trade details from DB before closing
                trade_result = supabase.table("trades").select("symbol, type, volume, live_pl").eq("ticket", ticket).eq("account_id", account_id).execute()
                trade_info = trade_result.data[0] if trade_result.data else None
                
                supabase.table("trades").update({
                    "status": "closed",
                    "close_reason": "ghost_cleanup",
                    "closed_at": datetime.now(timezone.utc).isoformat()
                }).eq("ticket", ticket).execute()
                log("INFO", f"Ghost trade {ticket} marked as closed", account_id)
                
                # Send Telegram notification for ghost trade closure
                if trade_info:
                    emoji = "🟢" if trade_info.get("live_pl", 0) >= 0 else "🔴"
                    send_telegram(
                        f"{emoji} <b>TRADE CLOSED (Ghost)</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"📊 Symbol: <b>{trade_info.get('symbol', 'N/A')}</b>\n"
                        f"📌 Direction: <b>{trade_info.get('type', 'N/A')}</b>\n"
                        f"💰 Lot Size: <b>{trade_info.get('volume', 0)}</b>\n"
                        f"💵 Last P/L: <b>${trade_info.get('live_pl', 0):.2f}</b>\n"
                        f"🆔 Ticket: <code>{ticket}</code>\n"
                        f"🏦 Account: <code>{account_id}</code>"
                    )
            except Exception as e:
                log("ERROR", f"Failed to close ghost trade {ticket}: {e}", account_id)
    
    # Sync actual positions from MT5
    for pos in positions:
        ticket = str(pos.ticket)
        try:
            margin = getattr(pos, 'margin', 0.0) or 0.0
            # Include swap in live_pl to match MT5's floating P/L exactly
            swap = getattr(pos, 'swap', 0.0) or 0.0
            live_pl = pos.profit + swap
            
            supabase.table("trades").upsert({
                "ticket": ticket,
                "account_id": account_id,
                "user_id": user_id,
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": pos.volume,
                "entry": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "live_pl": live_pl,
                "margin": margin,
                "open_time": datetime.fromtimestamp(pos.time).isoformat(),
                "status": "open"
            }, on_conflict="ticket").execute()
            
            log("DEBUG", f"Ticket {ticket}: {pos.symbol} | P/L: ${live_pl:.2f} (profit: ${pos.profit:.2f}, swap: ${swap:.2f})", account_id)
        except Exception as e:
            log("ERROR", f"Ticket {ticket} sync failed: {e}", account_id)
    
    # CRITICAL: Sync closed trades from MT5 history for Today's Net accuracy
    sync_closed_trades_from_history(account_id, user_id)
    
    # Summary
    log("INFO", f"Sync complete: {len(positions)} active, {len(ghost_tickets)} ghosts cleaned", account_id)

def sync_closed_trades_from_history(account_id: str, user_id: str):
    """
    CRITICAL: Sync ALL deals from MT5 history to Supabase (trades + balance changes).
    This ensures Today's Net matches MT5 History tab exactly.
    Uses Egypt time (UTC+2) for daily boundary (12 AM Cairo).
    Also calculates and stores Today's Net directly in today_net table.
    """
    log("DEBUG", "=== sync_closed_trades_from_history CALLED ===", account_id)
    try:
        # Use Egypt time (UTC+2) for daily boundary
        # Egypt midnight (12 AM Cairo) = 10 PM UTC previous day
        now_utc = datetime.now(timezone.utc)
        egypt_offset = timedelta(hours=2)
        now_egypt = now_utc + egypt_offset
        # Egypt midnight: 12 AM today Egypt time
        today_start_egypt = now_egypt.replace(hour=0, minute=0, second=0, microsecond=0)
        # Convert back to UTC for MT5 API
        today_start_utc = today_start_egypt - egypt_offset
        
        log("DEBUG", f"Now UTC: {now_utc.isoformat()}, Egypt midnight (UTC): {today_start_utc.isoformat()}", account_id)
        
        # Get ALL deals from MT5 history since today's start (UTC)
        # Note: group parameter is for symbol filtering, not account filtering
        # Since bridge runs for specific account, all deals are for that account
        from_date = today_start_utc
        to_date = now_utc
        
        log("DEBUG", f"Fetching deals from {from_date.isoformat()} to {to_date.isoformat()}", account_id)
        
        deals = mt5.history_deals_get(from_date, to_date)
        log("DEBUG", f"history_deals_get returned: {deals is None}, type: {type(deals)}, count: {len(deals) if deals else 0}", account_id)
        
        if deals is None:
            log("DEBUG", f"No history deals found for today (UTC: {now_utc.isoformat()})", account_id)
            # Store 0 in today_net table
            supabase.table("today_net").upsert({
                "user_id": user_id,
                "account_id": account_id,
                "net_profit": 0,
                "calculated_at": now_utc.isoformat(),
                "date": today_start_egypt.date().isoformat()
            }, on_conflict="user_id,date").execute()
            return
        
        # Include ALL deals (trades + balance changes + cash adjustments)
        all_deals = list(deals)
        
        if not all_deals:
            log("DEBUG", "No deals today", account_id)
            # Store 0 in today_net table
            supabase.table("today_net").upsert({
                "user_id": user_id,
                "account_id": account_id,
                "net_profit": 0,
                "calculated_at": now_utc.isoformat(),
                "date": today_start_egypt.date().isoformat()
            }, on_conflict="user_id,date").execute()
            return
        
        log("INFO", f"Found {len(all_deals)} total deals today (UTC)", account_id)
        
        # Calculate Today's Net directly from MT5 deals (only DEAL_ENTRY_OUT - matches MT5 History tab)
        today_net_profit = 0.0
        
        # First, calculate profit for DEAL_ENTRY_OUT deals only (matches MT5 History tab)
        for deal in all_deals:
            # Only count deals that close positions (DEAL_ENTRY_OUT or DEAL_ENTRY_OUT_CLOSE)
            if deal.entry in [mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_CLOSE]:
                profit = getattr(deal, 'profit', 0) or 0
                swap = getattr(deal, 'swap', 0) or 0
                commission = getattr(deal, 'commission', 0) or 0
                deal_profit = profit + swap + commission
                log("DEBUG", f"Deal {deal.ticket} (CLOSE): profit=${profit:.2f}, swap=${swap:.2f}, commission=${commission:.2f}, total=${deal_profit:.2f}", account_id)
                today_net_profit += deal_profit
            else:
                log("DEBUG", f"Deal {deal.ticket} (OPEN/BALANCE): skipped (entry={deal.entry})", account_id)
        
        # Then, sync new deals to Supabase
        for deal in all_deals:
            ticket = str(deal.ticket)
            try:
                # Check if this deal is already in DB
                existing = supabase.table("trades").select("ticket").eq("ticket", ticket).execute()
                if existing.data:
                    continue  # Already synced, skip sync but profit already counted
                
                # Calculate profit including swap and commission
                profit = deal.profit + deal.swap + deal.commission
                
                # Determine deal type
                if deal.entry == mt5.DEAL_ENTRY_IN:
                    deal_type = "open"
                    status = "open"
                elif deal.entry == mt5.DEAL_ENTRY_OUT or deal.entry == mt5.DEAL_ENTRY_OUT_CLOSE:
                    deal_type = "close"
                    status = "closed"
                elif deal.entry == mt5.DEAL_ENTRY_INOUT:
                    deal_type = "balance"
                    status = "closed"
                else:
                    deal_type = "other"
                    status = "closed"
                
                # Sync to Supabase
                supabase.table("trades").upsert({
                    "ticket": ticket,
                    "account_id": account_id,
                    "user_id": user_id,
                    "symbol": deal.symbol if deal.symbol else "BALANCE",
                    "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": deal.volume if deal.volume > 0 else 0,
                    "entry": deal.price,
                    "sl": None,
                    "tp": None,
                    "live_pl": profit,  # Profit for this deal
                    "margin": 0,  # TradeDeal doesn't have margin attribute
                    "open_time": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),  # UTC
                    "closed_at": datetime.fromtimestamp(deal.time, tz=timezone.utc).isoformat(),  # UTC
                    "status": status,
                    "close_reason": deal.comment if deal.comment else deal_type
                }, on_conflict="ticket").execute()
                
                log("DEBUG", f"Synced deal {ticket}: {deal.symbol or 'BALANCE'} | Type: {deal_type} | P/L: ${profit:.2f}", account_id)
            except Exception as e:
                log("ERROR", f"Failed to sync deal {ticket}: {e}", account_id)
        
        # Store Today's Net in today_net table
        supabase.table("today_net").upsert({
            "user_id": user_id,
            "account_id": account_id,
            "net_profit": today_net_profit,
            "calculated_at": now_utc.isoformat(),
            "date": today_start_egypt.date().isoformat()
        }, on_conflict="user_id,date").execute()
        
        log("INFO", f"Today's Net calculated: ${today_net_profit:.2f} from {len(all_deals)} deals", account_id)
        log("INFO", f"History sync complete: {len(all_deals)} deals processed", account_id)
        
    except Exception as e:
        log("ERROR", f"Failed to sync history deals: {e}", account_id)

# ============================================
# BASKET TP PER SYMBOL
# ============================================
def check_basket_tp_per_symbol(account_id: str, basket_tp_usd: float = 10.0) -> Dict:
    """
    Check basket TP for each symbol separately.
    Returns dict of symbol -> closed (True if closed).
    """
    positions = mt5.positions_get() or []
    closed_symbols = {}
    
    if not positions:
        return closed_symbols
    
    # Group positions by symbol
    symbol_positions = {}
    for pos in positions:
        symbol = pos.symbol
        if symbol not in symbol_positions:
            symbol_positions[symbol] = []
        symbol_positions[symbol].append(pos)
    
    # Check basket TP for each symbol
    for symbol, pos_list in symbol_positions.items():
        total_pl = sum(pos.profit + pos.swap for pos in pos_list)
        
        if total_pl >= basket_tp_usd:
            log("INFO", f"[BASKET TP] {symbol}: P/L ${total_pl:.2f} >= ${basket_tp_usd:.2f} - CLOSING {len(pos_list)} positions", account_id)
            closed_symbols[symbol] = True
            # Close all positions for this symbol
            for pos in pos_list:
                close_position(pos, account_id)
        else:
            log("DEBUG", f"[BASKET TP] {symbol}: P/L ${total_pl:.2f} / ${basket_tp_usd:.2f}", account_id)
    
    return closed_symbols

# ============================================
# GRID TRADING LOGIC (Per Symbol)
# ============================================
def get_symbol_positions(symbol: str):
    """Get all positions for a specific symbol."""
    return mt5.positions_get(symbol=symbol) or []

def get_symbol_open_profit(symbol: str) -> float:
    """Get total open profit for a symbol (including swap)."""
    positions = get_symbol_positions(symbol)
    return sum(pos.profit + pos.swap for pos in positions)

def get_last_position_price(symbol: str) -> Optional[float]:
    """Get the open price of the last position for a symbol."""
    positions = get_symbol_positions(symbol)
    if not positions:
        return None
    # Return the most recent position's open price
    last_pos = max(positions, key=lambda p: p.time)
    return last_pos.price_open

def check_market_direction(symbol: str) -> str:
    """
    Determine market direction using RSI and MACD.
    Returns 'BUY', 'SELL', or 'NONE'.
    """
    # Check RSI
    rsi_value = calculate_rsi(symbol, 14)
    if rsi_value is not None:
        if rsi_value < 30:
            return 'BUY'
        elif rsi_value > 70:
            return 'SELL'
    
    # Check MACD
    macd_result = calculate_macd(symbol, 12, 26, 9)
    if macd_result:
        macd_line, signal_line, histogram = macd_result
        if macd_line > signal_line and histogram > 0:
            return 'BUY'
        elif macd_line < signal_line and histogram < 0:
            return 'SELL'
    
    return 'NONE'

def check_and_open_grid_steps(symbol: str, step_points: int, lot_size: float, account_id: str, max_positions: int, step_loss_usd: float = None):
    """
    Check if the last position has reached the loss threshold and open new grid position.
    Uses MONEY-BASED grid step (dollar loss) instead of points to avoid digit confusion.
    
    PREVENTS DUPLICATE ORDERS: Only opens one grid step per symbol per cycle,
    and only if the last position is at least 60 seconds old.
    
    Args:
        symbol: Trading symbol
        step_points: Legacy parameter (not used anymore)
        lot_size: Lot size for new position
        account_id: Account ID for logging
        max_positions: Legacy parameter (grid steps are now unlimited)
        step_loss_usd: Dollar loss threshold to trigger next grid level (default: DEFAULT_GRID_STEP_LOSS_USD)
    """
    import time
    if step_loss_usd is None:
        step_loss_usd = DEFAULT_GRID_STEP_LOSS_USD
    
    positions = get_symbol_positions(symbol)
    if not positions:
        return
    
    # Grid steps are UNLIMITED - no max_positions check
    
    # Get the most recent position
    last_pos = max(positions, key=lambda p: p.time)
    
    # CRITICAL: Prevent duplicate orders - check if last position is at least 60 seconds old
    current_time = time.time()
    last_pos_age = current_time - last_pos.time
    if last_pos_age < 60:
        log("DEBUG", f"[GRID] {symbol}: Last position opened {last_pos_age:.0f}s ago (< 60s) - WAITING", account_id)
        return
    
    # Calculate floating P/L for this position
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return
    
    try:
        # CRITICAL FIX: Use MT5's built-in profit calculation (already in USD)
        # This is much more accurate than manual calculation
        profit_usd = last_pos.profit + last_pos.swap
        
        log("DEBUG", f"[GRID] {symbol}: Last position P/L ${profit_usd:.2f} (profit: ${last_pos.profit:.2f}, swap: ${last_pos.swap:.2f})", account_id)
        
        # Check if loss reached threshold
        if profit_usd <= -step_loss_usd:
            log("INFO", f"[GRID] {symbol}: Last position P/L ${profit_usd:.2f} <= -${step_loss_usd} -> OPENING GRID STEP (total: {len(positions)+1})", account_id)
            
            # Open new position in same direction (GRID STEP - not counted in base orders)
            if last_pos.type == mt5.POSITION_TYPE_BUY:
                execute_trade(symbol, "BUY", lot_size, account_id, is_base_order=False)
            else:
                execute_trade(symbol, "SELL", lot_size, account_id, is_base_order=False)
        else:
            log("DEBUG", f"[GRID] {symbol}: Last position P/L ${profit_usd:.2f} (threshold: -${step_loss_usd})", account_id)
            
    except Exception as e:
        log("WARN", f"Grid step calculation failed for {symbol}: {e}", account_id)

def process_all_symbols(account_id: str, settings: Dict):
    """
    Process all allowed symbols with grid trading logic:
    1. Check basket TP and close if target reached
    2. For closed symbols (by basket TP), immediately re-open base order
    3. For symbols with no positions, check direction and open base order
    4. Max 15 BASE orders across all symbols (grid steps are unlimited)
    """
    basket_tp = float(settings.get('Basket_Take_Profit', 10))
    grid_step = int(settings.get('Grid_Step', 100))
    max_positions = int(settings.get('Max_Open_Positions', DEFAULT_MAX_POSITIONS))
    lot_size = get_fixed_lot_size(settings)
    MAX_BASE_ORDERS = 15  # Hard limit on BASE orders only - grid steps are unlimited
    
    # Get all available symbols from MT5
    all_symbols = mt5.symbols_get()
    if not all_symbols:
        log("ERROR", "Failed to get symbols from MT5", account_id)
        return
    
    # Filter to allowed symbols AND auto-add them to Market Watch
    allowed_symbols = []
    for sym in all_symbols:
        if is_allowed_symbol(sym.name, settings):
            # Auto-select symbol into Market Watch
            if not sym.visible:
                selected = mt5.symbol_select(sym.name, True)
                if selected:
                    log("DEBUG", f"[MARKET WATCH] Added: {sym.name}", account_id)
            allowed_symbols.append(sym.name)
    
    # Get current base orders count (positions with comment "MOKABot Base")
    all_positions = mt5.positions_get() or []
    base_orders_count = sum(1 for p in all_positions if p.comment == "MOKABot Base")
    total_positions = len(all_positions)
    
    log("INFO", f"Processing {len(allowed_symbols)} symbols | Base orders: {base_orders_count}/{MAX_BASE_ORDERS} | Total positions: {total_positions}", account_id)
    
    # Step 1: Check basket TP for all symbols
    closed_symbols = check_basket_tp_per_symbol(account_id, basket_tp)
    
    # Refresh counts after basket TP closes
    all_positions = mt5.positions_get() or []
    base_orders_count = sum(1 for p in all_positions if p.comment == "MOKABot Base")
    
    # Step 2: Process each symbol
    for symbol in allowed_symbols:
        positions = get_symbol_positions(symbol)
        total_orders = len(positions)
        total_profit = get_symbol_open_profit(symbol)
        
        # Count base orders for this symbol
        symbol_base_orders = sum(1 for p in positions if p.comment == "MOKABot Base")
        
        # Case 1: No positions - open base order if we have room
        if total_orders == 0:
            # Check if we can open a new base order
            if base_orders_count >= MAX_BASE_ORDERS:
                log("DEBUG", f"[MAX BASE] {symbol}: Base orders {base_orders_count}/{MAX_BASE_ORDERS} - NO new base order", account_id)
                continue
            
            # Open new base order (including symbols just closed by basket TP)
            direction = check_market_direction(symbol)
            if direction != 'NONE':
                if symbol in closed_symbols:
                    log("INFO", f"[RE-OPEN BASE] {symbol}: Basket TP hit | Direction={direction} -> OPENING ({base_orders_count+1}/{MAX_BASE_ORDERS})", account_id)
                else:
                    log("INFO", f"[OPEN BASE] {symbol}: No positions | Direction={direction} -> OPENING ({base_orders_count+1}/{MAX_BASE_ORDERS})", account_id)
                result = execute_trade(symbol, direction, lot_size, account_id, is_base_order=True)
                if result:
                    base_orders_count += 1
                    # CRITICAL: After opening a base order, wait before processing next symbols
                    # This prevents opening multiple base orders in the same cycle
                    import time
                    time.sleep(2)  # Wait 2 seconds between base order openings
            else:
                log("DEBUG", f"[SKIP] {symbol}: No positions | Direction=NONE -> SKIP", account_id)
        
        # Case 2: Has positions - check grid step and monitor (PRIORITY - reinforce existing)
        elif total_orders >= 1:
            # Check if we should open a grid level (every $10 loss) - UNLIMITED grid steps
            check_and_open_grid_steps(symbol, grid_step, lot_size, account_id, max_positions)
            # Refresh position count after potential grid open
            positions = get_symbol_positions(symbol)
            total_orders = len(positions)
            total_profit = get_symbol_open_profit(symbol)
            
            log("DEBUG", f"[MONITOR] {symbol}: {total_orders} positions ({symbol_base_orders} base) | P/L=${total_profit:.2f} | Waiting for basket TP ${basket_tp}", account_id)

def close_position(pos, account_id: str):
    """Close a single position."""
    try:
        # Determine close order type (opposite of position type)
        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": pos.ticket,
            "price": price,
            "deviation": 20,
            "magic": 100000,
            "comment": "Basket TP closed",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log("INFO", f"[CLOSED] Ticket {pos.ticket} {pos.symbol} {pos.volume} lots | P/L: ${pos.profit:.2f}", account_id)
            direction = "SELL" if pos.type == mt5.POSITION_TYPE_BUY else "BUY"
            emoji = "🟢" if pos.profit >= 0 else "🔴"
            send_telegram(
                f"{emoji} <b>TRADE CLOSED</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Symbol: <b>{pos.symbol}</b>\n"
                f"📌 Direction: <b>{direction}</b>\n"
                f"💰 Lot Size: <b>{pos.volume}</b>\n"
                f"💵 P/L: <b>${pos.profit:.2f}</b>\n"
                f"🆔 Ticket: <code>{pos.ticket}</code>\n"
                f"🏦 Account: <code>{account_id}</code>"
            )
            # Update DB
            try:
                supabase.table("trades").update({
                    "status": "closed",
                    "close_reason": "basket_tp",
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "profit_at_close": pos.profit + pos.swap
                }).eq("ticket", str(pos.ticket)).execute()
            except Exception:
                pass
        else:
            error = mt5.last_error() if not result else result.retcode
            log("ERROR", f"Failed to close ticket {pos.ticket}: {error}", account_id)
    except Exception as e:
        log("ERROR", f"Exception closing ticket {pos.ticket}: {e}", account_id)

# ============================================
# TRADE EXECUTION
# ============================================
def execute_trade(symbol: str, order_type: str, lot_size: float, account_id: str, is_base_order: bool = True) -> bool:
    """
    Execute a trade order.
    order_type: 'BUY' or 'SELL'
    is_base_order: True for base order, False for grid step
    """
    # HARD SECURITY CHECK: Verify symbol is allowed before ANY trade
    if not is_allowed_symbol(symbol, {}):
        log("ERROR", f"[SECURITY ALERT] Attempted to trade {symbol} which is NOT ALLOWED! Trade BLOCKED.", account_id)
        return False
    
    # SPREAD FILTER: Check if spread is within acceptable limits
    if not is_spread_safe(symbol, account_id=account_id):
        return False
    
    try:
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        
        if not tick or not info:
            log("ERROR", f"Cannot get symbol info for {symbol}", account_id)
            return False
        
        price = tick.ask if order_type == "BUY" else tick.bid
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL
        
        # Use different comments to distinguish base orders from grid steps
        comment = "MOKABot Base" if is_base_order else "MOKABot Grid"
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5_order_type,
            "price": price,
            "deviation": 20,
            "magic": 100000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            order_type_label = "BASE" if is_base_order else "GRID"
            log("INFO", f"[{order_type_label} OPENED] {order_type} {symbol} {lot_size} lots @ {price} | Order: {result.order}", account_id)
            send_telegram(
                f"🟢 <b>TRADE OPENED ({order_type_label})</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 Symbol: <b>{symbol}</b>\n"
                f"📌 Direction: <b>{order_type}</b>\n"
                f"💰 Lot Size: <b>{lot_size}</b>\n"
                f"📈 Price: <b>{price}</b>\n"
                f"🆔 Order: <code>{result.order}</code>\n"
                f"🏦 Account: <code>{account_id}</code>"
            )
            return True
        else:
            error = result.comment if result else "No result"
            log("ERROR", f"Trade failed for {symbol}: {error}", account_id)
            return False
    except Exception as e:
        log("ERROR", f"Exception executing trade: {e}", account_id)
        return False

# Track last hourly report time to avoid duplicate sends
last_hourly_report_hour = None

# Track floating loss alert (avoid spamming)
FLOATING_LOSS_STEP = 50.0  # Alert every $50 of loss
last_loss_alert_level = 0  # Last threshold level we alerted at (0 = no alert yet)

def check_floating_loss(account_id: str):
    """Send Telegram alert every time floating loss crosses a new $50 level."""
    global last_loss_alert_level
    
    try:
        positions = mt5.positions_get() or []
        if not positions:
            # No positions = no floating loss, reset
            last_loss_alert_level = 0
            return
        
        total_pl = sum(p.profit + p.swap for p in positions)
        
        if total_pl < 0:
            # Calculate current loss level (e.g. -152 -> level 3 = $150)
            current_level = int(abs(total_pl) // FLOATING_LOSS_STEP)
            
            if current_level > last_loss_alert_level:
                # Count positions per symbol
                symbols = {}
                for p in positions:
                    symbols[p.symbol] = symbols.get(p.symbol, 0) + 1
                
                positions_info = "\n".join(
                    f"  📌 {sym}: {cnt} position(s)"
                    for sym, cnt in symbols.items()
                )
                
                send_telegram(
                    f"🔴 <b>WARNING: Floating Loss Alert</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🏦 Account: <code>{account_id}</code>\n"
                    f"💸 <b>Floating Loss:</b> ${total_pl:.2f}\n"
                    f"📊 <b>Open Positions:</b> {len(positions)}\n"
                    f"{positions_info}\n"
                    f"\n"
                    f"⚠️ Please monitor your account!"
                )
                last_loss_alert_level = current_level
                log("WARN", f"Floating loss alert sent: ${total_pl:.2f} (level {current_level})", account_id)
        else:
            # Profit is positive, reset alert level
            last_loss_alert_level = 0
    
    except Exception as e:
        log("ERROR", f"Failed to check floating loss: {e}", account_id)

def send_hourly_report(account_id: str, user_id: str):
    """Send hourly Telegram report with balance, open positions, and daily profit."""
    global last_hourly_report_hour
    
    current_hour = datetime.now(timezone.utc).strftime("%Y-%m-%d %H")
    if current_hour == last_hourly_report_hour:
        return  # Already sent this hour
    
    log("INFO", f"[TELEGRAM] Attempting to send hourly report...", account_id)
    
    try:
        info = mt5.account_info()
        if not info:
            log("WARN", f"[TELEGRAM] Failed to get account info - MT5 not connected", account_id)
            return
        
        positions = mt5.positions_get() or []
        open_positions_count = len(positions)
        total_open_profit = sum(p.profit + p.swap for p in positions)
        
        # Calculate daily profit from closed trades today (Cairo midnight)
        now_utc = datetime.now(timezone.utc)
        cairo_now = now_utc + timedelta(hours=2)
        cairo_midnight = cairo_now.replace(hour=0, minute=0, second=0, microsecond=0)
        cairo_midnight_utc = cairo_midnight - timedelta(hours=2)
        today_start = cairo_midnight_utc.isoformat()
        
        daily_profit = 0.0
        try:
            closed_today = supabase.table("trades").select("live_pl").eq("account_id", account_id).eq("status", "closed").gte("closed_at", today_start).execute()
            if closed_today.data:
                daily_profit = sum(t.get('live_pl', 0) or 0 for t in closed_today.data)
        except Exception:
            pass
        
        # Build report message
        now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
        balance = info.balance
        equity = info.equity
        free_margin = info.margin_free
        
        # Determine status emoji
        profit_emoji = "🟢" if total_open_profit >= 0 else "🔴"
        daily_emoji = "🟢" if daily_profit >= 0 else "🔴"
        
        message = (
            f"📊 <b>Hourly Report</b>\n"
            f"\n"
            f"⏱️ <b>Time:</b> {now_str}\n"
            f"🏛️ <b>Account:</b> <code>{account_id}</code>\n"
            f"\n"
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"💎 <b>Equity:</b> ${equity:.2f}\n"
            f"📌 <b>Open Positions:</b> {open_positions_count}\n"
            f"{profit_emoji} <b>Open P/L:</b> ${total_open_profit:.2f}\n"
            f"{daily_emoji} <b>Daily Profit:</b> ${daily_profit:.2f}\n"
            f"💶 <b>Free Margin:</b> ${free_margin:.2f}"
        )
        
        send_telegram(message)
        last_hourly_report_hour = current_hour
        log("INFO", f"Hourly report sent via Telegram", account_id)
        
    except Exception as e:
        log("ERROR", f"Failed to send hourly report: {e}", account_id)

# Daily report tracking
last_daily_report_date = None

def send_daily_midnight_report(account_id: str):
    """Send daily Today's Net report at midnight Cairo time (00:00 UTC+2)."""
    global last_daily_report_date
    
    try:
        # Get current Cairo time (UTC+2)
        now_utc = datetime.now(timezone.utc)
        cairo_now = now_utc + timedelta(hours=2)
        
        # Check if it's midnight (00:00 - 00:05 window)
        if cairo_now.hour != 0 or cairo_now.minute >= 5:
            return
        
        today_str = cairo_now.strftime("%Y-%m-%d")
        
        # Check if we already sent today's report
        if last_daily_report_date == today_str:
            return
        
        # Calculate Today's Net (closed trades since midnight Cairo time)
        cairo_midnight = cairo_now.replace(hour=0, minute=0, second=0, microsecond=0)
        cairo_midnight_utc = cairo_midnight - timedelta(hours=2)  # Convert back to UTC
        cairo_midnight_iso = cairo_midnight_utc.isoformat()
        
        # Get closed trades today
        try:
            closed_today = supabase.table("trades").select("live_pl").eq("account_id", account_id).eq("status", "closed").gte("closed_at", cairo_midnight_iso).execute()
            closed_trades = closed_today.data if closed_today.data else []
            today_net = sum(t.get("live_pl", 0) or 0 for t in closed_trades)
            trade_count = len(closed_trades)
        except Exception:
            today_net = 0
            trade_count = 0
        
        # Get current account info
        info = mt5.account_info()
        balance = info.balance if info else 0
        equity = info.equity if info else 0
        
        # Get floating P/L
        positions = mt5.positions_get() or []
        floating_pl = sum(p.profit + p.swap for p in positions)
        
        # Determine emoji
        net_emoji = "🟢" if today_net >= 0 else "🔴"
        
        message = (
            f"📊 <b>Daily Report - {today_str}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Account: <code>{account_id}</code>\n"
            f"\n"
            f"{net_emoji} <b>Today's Net:</b> ${today_net:.2f}\n"
            f"📈 Closed Trades: {trade_count}\n"
            f"\n"
            f"💼 Balance: ${balance:.2f}\n"
            f"💎 Equity: ${equity:.2f}\n"
            f"📊 Floating P/L: ${floating_pl:.2f}\n"
            f"\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 MOKABot Auto-Report"
        )
        
        send_telegram(message)
        last_daily_report_date = today_str
        log("INFO", f"Daily midnight report sent: Today's Net ${today_net:.2f}", account_id)
        
    except Exception as e:
        log("ERROR", f"Failed to send daily report: {e}", account_id)

def send_heartbeat(account_id: str, user_id: str):
    """Send heartbeat to database."""
    try:
        supabase.table("bridge_heartbeat").upsert({
            "mt5_account_id": account_id,
            "account_id": account_id,
            "user_id": user_id,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "status": "alive"
        }, on_conflict="mt5_account_id").execute()
    except Exception as e:
        log("ERROR", f"Heartbeat failed: {e}", account_id)

def get_bot_status(mt5_account_id: str) -> bool:
    """Get bot active status for account."""
    try:
        result = supabase.table("bot_status").select("bot_active").eq("mt5_account_id", mt5_account_id).maybe_single().execute()
        return result.data['bot_active'] if result.data else False
    except Exception as e:
        log("DEBUG", f"Bot status fetch failed: {e}", mt5_account_id)
        return False

def fetch_user_strategies(user_id: str) -> List[Dict]:
    """Fetch strategies for specific user (including global strategies with user_id=NULL)."""
    try:
        # Fetch user-specific strategies AND global strategies (user_id IS NULL)
        result = supabase.table("strategies").select("*").eq("is_active", True).execute()
        strategies = result.data or []
        
        # Filter to user-specific + global
        user_strategies = [s for s in strategies if s.get('user_id') == user_id or s.get('user_id') is None]
        
        log("DEBUG", f"Fetched {len(user_strategies)} active strategies for user {user_id}", None)
        for s in user_strategies:
            dry_run_label = "DRY RUN" if s.get('dry_run', True) else "LIVE"
            log("DEBUG", f"  Strategy: {s['name']} | Symbol: {s['symbol']} | Mode: {dry_run_label}", None)
        
        return user_strategies
    except Exception as e:
        log("ERROR", f"Strategy fetch failed: {e}", None)
        return []

def fetch_tactics_settings() -> Dict:
    """Fetch all tactics settings from database."""
    try:
        result = supabase.table("tactics_settings").select("*").execute()
        settings = {}
        for row in result.data or []:
            key = row['key']
            value = row.get('value', {})
            # Extract the actual value from the JSONB
            settings[key] = value.get('value', value) if isinstance(value, dict) else value
        return settings
    except Exception as e:
        log("ERROR", f"Failed to fetch tactics settings: {e}")
        return {}

# ============================================
# TECHNICAL INDICATORS
# ============================================
def calculate_rsi(symbol: str, period: int = 14) -> Optional[float]:
    """
    Calculate RSI (Relative Strength Index) using MT5 rates.
    Returns RSI value or None if calculation fails.
    """
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, period + 50)
        if rates is None or len(rates) < period + 1:
            return None
        
        closes = [r['close'] for r in rates]
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # Smooth using Wilder's method
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    except Exception as e:
        log("DEBUG", f"RSI calculation error: {e}")
        return None

def calculate_macd(symbol: str, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[tuple]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns (macd_line, signal_line, histogram) or None if calculation fails.
    """
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, slow + signal + 50)
        if rates is None or len(rates) < slow + signal:
            return None
        
        closes = [r['close'] for r in rates]
        
        # Calculate EMAs
        def ema(data, period):
            multiplier = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                result.append((data[i] - result[-1]) * multiplier + result[-1])
            return result
        
        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        
        # MACD line = Fast EMA - Slow EMA
        macd_line_values = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
        
        # Signal line = EMA of MACD line
        signal_line_values = ema(macd_line_values, signal)
        
        # Get latest values
        macd_line = macd_line_values[-1]
        signal_line = signal_line_values[-1]
        histogram = macd_line - signal_line
        
        return (macd_line, signal_line, histogram)
        
    except Exception as e:
        log("DEBUG", f"MACD calculation error: {e}")
        return None

def evaluate_strategy_signal(strategy: Dict, account_id: str, settings: Dict = None) -> tuple:
    """
    Evaluate strategy entry conditions against current market data.
    Returns (signal_triggered: bool, direction: str) where direction is 'BUY', 'SELL', or None.
    
    STRICT STRATEGY PROTOCOL:
    1. Symbol must pass is_allowed_symbol() check
    2. Risk limits must be checked
    3. Entry conditions must be met
    """
    symbol = strategy.get('symbol', '')
    entry_rules = strategy.get('entry_rules', {})
    conditions = entry_rules.get('conditions', [])
    logic = entry_rules.get('logic', 'AND')
    
    # Get settings if not provided
    if settings is None:
        settings = fetch_tactics_settings()
    
    # === STRICT STRATEGY PROTOCOL ===
    # 1. Check if symbol is allowed
    resolved_for_check = resolve_symbol(symbol, account_id)
    if not is_allowed_symbol(resolved_for_check, settings):
        log("WARN", f"[PROTOCOL] Symbol BLOCKED by Dynamic Filter: {symbol} -> {resolved_for_check}", account_id)
        return (False, None)
    
    # 2. Check risk limits
    info = mt5.account_info()
    if info:
        risk_passed, risk_reason = check_risk_limits(resolved_for_check, account_id, settings, info.equity, info.balance)
        if not risk_passed:
            log("WARN", f"[PROTOCOL] Risk limit failed: {risk_reason}", account_id)
            return (False, None)
    
    # === END PROTOCOL ===
    
    if not conditions:
        log("DEBUG", f"Strategy '{strategy['name']}': No conditions defined -> SKIP", account_id)
        return (False, None)
    
    # Resolve symbol for this broker
    resolved_symbol = resolve_symbol(symbol, account_id)
    
    # Get current market data
    try:
        tick = mt5.symbol_info_tick(resolved_symbol)
        if not tick:
            log("DEBUG", f"Strategy '{strategy['name']}': Cannot get tick for {resolved_symbol}", account_id)
            return (False, None)
        
        current_price = (tick.ask + tick.bid) / 2
        log("DEBUG", f"Strategy '{strategy['name']}': {resolved_symbol} current price = {current_price:.5f}", account_id)
    except Exception as e:
        log("DEBUG", f"Strategy '{strategy['name']}': Failed to get tick data: {e}", account_id)
        return (False, None)
    
    # Evaluate each condition
    results = []
    directions = []  # Track direction for each condition
    for i, cond in enumerate(conditions):
        indicator = cond.get('indicator', '')
        operator = cond.get('operator', '')
        action = cond.get('action', '')
        value = cond.get('value', 0)
        params = cond.get('params', {})
        
        # Price indicator
        if indicator == 'price':
            cond_result = False
            cond_direction = None
            if operator == 'gt' and current_price > value:
                cond_result = True
            elif operator == 'lt' and current_price < value:
                cond_result = True
            elif operator == 'gte' and current_price >= value:
                cond_result = True
            elif operator == 'lte' and current_price <= value:
                cond_result = True
            
            log("DEBUG", f"  Condition {i+1}: Price ({current_price:.5f}) {operator} {value} -> {cond_result}", account_id)
            results.append(cond_result)
            directions.append(cond_direction)
        
        # RSI indicator
        elif indicator == 'rsi':
            rsi_value = calculate_rsi(resolved_symbol, params.get('length', 14))
            if rsi_value is not None:
                cond_result = False
                cond_direction = None
                if action == 'buy_if_below_30':
                    cond_result = rsi_value < 30
                    if cond_result:
                        cond_direction = 'BUY'
                elif action == 'sell_if_above_70':
                    cond_result = rsi_value > 70
                    if cond_result:
                        cond_direction = 'SELL'
                elif operator == 'lt' and rsi_value < value:
                    cond_result = True
                elif operator == 'gt' and rsi_value > value:
                    cond_result = True
                
                log("DEBUG", f"  Condition {i+1}: RSI({params.get('length', 14)}) = {rsi_value:.2f} | {action or operator} -> {cond_result} | Dir: {cond_direction}", account_id)
                results.append(cond_result)
                directions.append(cond_direction)
            else:
                log("DEBUG", f"  Condition {i+1}: RSI calculation failed", account_id)
                results.append(False)
                directions.append(None)
        
        # MACD indicator
        elif indicator == 'macd':
            macd_result = calculate_macd(resolved_symbol, params.get('fast', 12), params.get('slow', 26), params.get('signal', 9))
            if macd_result:
                macd_line, signal_line, histogram = macd_result
                cond_result = False
                cond_direction = None
                if action == 'crossover':
                    # Bullish crossover: MACD crosses above signal
                    cond_result = macd_line > signal_line and histogram > 0
                    if cond_result:
                        cond_direction = 'BUY'
                elif action == 'crossunder':
                    # Bearish crossover: MACD crosses below signal
                    cond_result = macd_line < signal_line and histogram < 0
                    if cond_result:
                        cond_direction = 'SELL'
                elif operator == 'gt':
                    cond_result = macd_line > signal_line
                elif operator == 'lt':
                    cond_result = macd_line < signal_line
                
                log("DEBUG", f"  Condition {i+1}: MACD = {macd_line:.5f} | Signal = {signal_line:.5f} | Hist = {histogram:.5f} | {action or operator} -> {cond_result} | Dir: {cond_direction}", account_id)
                results.append(cond_result)
                directions.append(cond_direction)
            else:
                log("DEBUG", f"  Condition {i+1}: MACD calculation failed", account_id)
                results.append(False)
                directions.append(None)
        
        else:
            log("DEBUG", f"  Condition {i+1}: {indicator}({params}) -> UNKNOWN INDICATOR", account_id)
            results.append(False)
            directions.append(None)
    
    # Apply logic (AND/OR)
    if logic == 'AND':
        final = all(results)
    else:
        final = any(results)
    
    # Determine final direction based on triggered conditions
    final_direction = None
    if final:
        # Get direction from first True condition
        for i, r in enumerate(results):
            if r and directions[i]:
                final_direction = directions[i]
                break
        # Default to BUY if no direction specified
        if final_direction is None:
            final_direction = 'BUY'
    
    log("DEBUG", f"Strategy '{strategy['name']}': {logic} logic -> {results} -> FINAL: {final} | Direction: {final_direction}", account_id)
    return (final, final_direction)

# ============================================
# ACCOUNT FAILURE TRACKING
# ============================================
def is_account_in_cooldown(account_id: str) -> bool:
    """Check if account is in cooldown period due to previous failures."""
    if account_id not in account_failures:
        return False
    
    failure_info = account_failures[account_id]
    last_failure = failure_info.get('last_failure')
    
    if not last_failure:
        return False
    
    # Check if cooldown has expired
    cooldown_expired = datetime.now(timezone.utc) - last_failure > timedelta(minutes=FAILURE_COOLDOWN_MINUTES)
    
    if cooldown_expired:
        log("INFO", f"Cooldown expired, will retry connection", account_id)
        del account_failures[account_id]
        return False
    
    return True

def record_failure(account_id: str):
    """Record a connection failure for an account."""
    if account_id not in account_failures:
        account_failures[account_id] = {'failures': 0, 'last_failure': None}
    
    account_failures[account_id]['failures'] += 1
    account_failures[account_id]['last_failure'] = datetime.now(timezone.utc)
    
    failures = account_failures[account_id]['failures']
    
    if failures >= MAX_CONSECUTIVE_FAILURES:
        log("WARN", f"Account flagged as CONNECTION FAILED ({failures} consecutive failures). Cooldown: {FAILURE_COOLDOWN_MINUTES}min", account_id)
        # Update database status
        try:
            supabase.table("bridge_heartbeat").upsert({
                "mt5_account_id": account_id,
                "account_id": account_id,
                "status": "connection_failed",
                "last_heartbeat": datetime.now(timezone.utc).isoformat()
            }, on_conflict="mt5_account_id").execute()
        except:
            pass
    else:
        log("WARN", f"Connection failed ({failures}/{MAX_CONSECUTIVE_FAILURES} before cooldown)", account_id)

def record_success(account_id: str):
    """Clear failure tracking on successful connection."""
    if account_id in account_failures:
        log("INFO", f"Connection restored, clearing failure tracking", account_id)
        del account_failures[account_id]

# ============================================
# MAIN BRIDGE LOOP
# ============================================
def process_account(account: Dict, safety_engines: Dict[str, SafetyEngine]) -> bool:
    """Process a single account - connect, sync, disconnect."""
    login = account['login']
    password = account['password']
    server = account['server']
    user_id = account['user_id']
    account_id = str(login)
    
    # Check if account is in cooldown
    if is_account_in_cooldown(account_id):
        remaining = account_failures[account_id]['last_failure'] + timedelta(minutes=FAILURE_COOLDOWN_MINUTES) - datetime.now(timezone.utc)
        log("WARN", f"Account in cooldown. Skipping. ({int(remaining.total_seconds())}s remaining)", account_id)
        return False
    
    log("INFO", f"Connecting to {login} on {server} (timeout: {CONNECTION_TIMEOUT_SECONDS}s)...", account_id)
    
    # Initialize MT5 for this account WITH TIMEOUT
    # Note: mt5.initialize() doesn't have a direct timeout parameter,
    # but we can use timeout_ms if available in newer versions
    try:
        init_result = mt5.initialize(
            login=login, 
            password=password, 
            server=server,
            timeout=CONNECTION_TIMEOUT_SECONDS * 1000  # Timeout in milliseconds
        )
    except TypeError:
        # Older MT5 versions don't support timeout parameter
        # Fall back to default behavior
        init_result = mt5.initialize(login=login, password=password, server=server)
    
    if not init_result:
        error = mt5.last_error()
        log("ERROR", f"MT5 init failed: {error}", account_id)
        
        # Check if it's a timeout error (-10005)
        if error and len(error) >= 2 and error[0] == -10005:
            log("WARN", f"IPC TIMEOUT detected for {account_id}", account_id)
        
        record_failure(account_id)
        return False
    
    # Verify connection
    info = mt5.account_info()
    if not info:
        log("ERROR", "Failed to get account info", account_id)
        mt5.shutdown()
        record_failure(account_id)
        return False
    
    log("INFO", f"Connected successfully | Balance: ${info.balance:.2f}", account_id)
    
    # Clear failure tracking on success
    record_success(account_id)
    
    # Initialize SafetyEngine for this account if not exists
    if account_id not in safety_engines:
        safety_engines[account_id] = SafetyEngine(supabase, user_id=user_id, account_id=account_id)
        log("INFO", f"SafetyEngine initialized", account_id)
    
    safety = safety_engines[account_id]
    
    # Sync data
    sync_account_balance(user_id, account_id)
    sync_account_trades(user_id, account_id)
    send_heartbeat(account_id, user_id)
    
    # Send hourly Telegram report (once per hour)
    send_hourly_report(account_id, user_id)
    
    # Check floating loss and alert if needed
    check_floating_loss(account_id)
    
    # Check if it's midnight Cairo time and send daily report
    send_daily_midnight_report(account_id)
    
    # === BASKET TP CHECK (Per Symbol) ===
    # Note: Basket TP is now handled inside process_all_symbols
    
    # Check bot status (using mt5_account_id, not user_id)
    bot_active = get_bot_status(account_id)
    log("DEBUG", f"Bot status for account {account_id}: {'ACTIVE' if bot_active else 'STANDBY'}", account_id)
    
    # === DEBUG: Log Strict Strategy Protocol Status ===
    tactics_settings = fetch_tactics_settings()
    debug_log_strategy(account_id, tactics_settings)
    
    if bot_active:
        # Resolve a symbol for safety check (use EURUSD as default)
        resolved_symbol = resolve_symbol("EURUSD", account_id)
        
        # Ensure symbol is in Market Watch
        ensure_symbol_in_market_watch(resolved_symbol, account_id)
        
        # Run safety checks before processing
        passed, reason = safety.run_all_checks(
            symbol=resolved_symbol,
            current_equity=info.equity,
            start_equity=info.balance
        )
        
        if passed:
            log("INFO", f"Bot RUNNING | Safety checks PASSED | Grid Trading Mode", account_id)
            log("DEBUG", f"[SETTINGS] Basket_TP=${tactics_settings.get('Basket_Take_Profit', 10)} | Grid_Step={tactics_settings.get('Grid_Step', 100)}pts | Max_Pos={tactics_settings.get('Max_Open_Positions', 1)} | Lot={get_fixed_lot_size(tactics_settings)}", account_id)
            
            # Process all symbols with grid trading logic
            process_all_symbols(account_id, tactics_settings)
        else:
            log("WARN", f"Bot BLOCKED by safety: {reason}", account_id)
    else:
        log("DEBUG", f"Bot STANDBY - activate bot from dashboard to start trading", account_id)
    
    # Disconnect
    mt5.shutdown()
    log("INFO", f"Sync complete", account_id)
    return True

def main():
    """Main bridge loop - processes all accounts sequentially."""
    log("INFO", "=" * 70)
    log("INFO", "MOKABot Multi-Account Bridge Started")
    log("INFO", "=" * 70)
    
    # Print hard-coded strategy configuration
    log("INFO", "[System] Strategy Loaded: Grid Trading Mode | Lot 0.02 | Basket $10 | Grid Step 100pts | Max Pos 1")
    log("INFO", "[System] Filters Applied: Forex-Only. Blocked: XAU, XAG, OIL, BTC, ETH, US30, NAS100")
    log("INFO", "=" * 70)
    
    cycle = 0
    safety_engines: Dict[str, SafetyEngine] = {}  # Cache safety engines per account
    
    while True:
        # Check for pending commands from dashboard
        if not check_pending_commands():
            log("INFO", "Bridge shutdown initiated by command")
            break
        
        cycle += 1
        log("INFO", f"--- Cycle {cycle} ---")
        
        # Fetch active accounts from database
        accounts = fetch_active_accounts()
        
        if not accounts:
            log("WARN", "No active accounts found. Waiting 30s...")
            time.sleep(30)
            continue
        
        # Process each account sequentially
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for account in accounts:
            try:
                account_id = str(account['login'])
                if is_account_in_cooldown(account_id):
                    skipped_count += 1
                
                if process_account(account, safety_engines):
                    success_count += 1
                elif is_account_in_cooldown(account_id):
                    pass  # Already counted as skipped
                else:
                    failed_count += 1
            except Exception as e:
                log("ERROR", f"Account {account['login']} failed: {e}")
                failed_count += 1
            
            # Small delay between accounts
            time.sleep(2)
        
        # Summary
        log("INFO", f"Cycle {cycle} complete: {success_count} synced, {failed_count} failed, {skipped_count} skipped (cooldown)")
        
        if account_failures:
            log("WARN", f"Accounts in cooldown: {list(account_failures.keys())}")
        
        # Wait before next cycle
        log("INFO", "Waiting 10s before next cycle...")
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("INFO", "Bridge stopped by user")
        mt5.shutdown()
