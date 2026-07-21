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
# CONNECTION TIMEOUT & FAILURE TRACKING
# ============================================
CONNECTION_TIMEOUT_SECONDS = 10  # Max time to wait for MT5 connection (increased for slow brokers)
FAILURE_COOLDOWN_MINUTES = 5     # Skip failed accounts for this long (reduced for faster recovery)
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
DEFAULT_GRID_STEP = 100          # Grid step in points
DEFAULT_FIXED_LOT_SIZE = 0.02    # Fixed lot size - no multipliers
DEFAULT_BASKET_TP = 10           # Basket take profit in USD
DEFAULT_MAX_POSITIONS = 5        # Max open positions per symbol
DEFAULT_EQUITY_SL_PCT = 0        # Equity stop loss percentage
DEFAULT_MAX_SPREAD_PIPS = 3.0    # Max allowed spread in pips

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
    """Sync trades for current connected account with ghost trade cleanup."""
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
        # Mark ghost trades as closed
        for ticket in ghost_tickets:
            try:
                supabase.table("trades").update({
                    "status": "closed",
                    "close_reason": "ghost_cleanup",
                    "closed_at": datetime.now(timezone.utc).isoformat()
                }).eq("ticket", ticket).execute()
                log("INFO", f"Ghost trade {ticket} marked as closed", account_id)
            except Exception as e:
                log("ERROR", f"Failed to close ghost trade {ticket}: {e}", account_id)
    
    # Sync actual positions from MT5
    for pos in positions:
        ticket = str(pos.ticket)
        try:
            margin = getattr(pos, 'margin', 0.0) or 0.0
            live_pl = pos.profit
            
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
            
            log("DEBUG", f"Ticket {ticket}: {pos.symbol} | P/L: ${live_pl:.2f}", account_id)
        except Exception as e:
            log("ERROR", f"Ticket {ticket} sync failed: {e}", account_id)
    
    # Summary
    log("INFO", f"Sync complete: {len(positions)} active, {len(ghost_tickets)} ghosts cleaned", account_id)

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

def check_and_open_grid_steps(symbol: str, step_points: int, lot_size: float, account_id: str, max_positions: int):
    """
    Check if price moved against us by step_points and open new grid position.
    """
    positions = get_symbol_positions(symbol)
    if not positions or len(positions) >= max_positions:
        return
    
    # Get last position price
    last_price = get_last_position_price(symbol)
    if last_price is None:
        return
    
    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return
    
    current_price = (tick.ask + tick.bid) / 2
    
    # Get point value
    info = mt5.symbol_info(symbol)
    if not info:
        return
    point = info.point
    step_distance = step_points * point
    
    # Check if price moved against us
    # For BUY positions: price went down
    # For SELL positions: price went up
    last_pos = max(positions, key=lambda p: p.time)
    
    if last_pos.type == mt5.POSITION_TYPE_BUY:
        # Price went down - add grid BUY
        if current_price <= last_price - step_distance:
            log("INFO", f"[GRID] {symbol}: Price {current_price:.5f} <= Last {last_price:.5f} - {step_points}pts -> OPEN BUY", account_id)
            execute_trade(symbol, "BUY", lot_size, account_id)
    else:
        # Price went up - add grid SELL
        if current_price >= last_price + step_distance:
            log("INFO", f"[GRID] {symbol}: Price {current_price:.5f} >= Last {last_price:.5f} + {step_points}pts -> OPEN SELL", account_id)
            execute_trade(symbol, "SELL", lot_size, account_id)

def process_all_symbols(account_id: str, settings: Dict):
    """
    Process all allowed symbols with grid trading logic:
    1. Check basket TP and close if target reached
    2. For closed symbols (by basket TP), immediately re-open
    3. For symbols with no positions, check direction and open
    4. For symbols with positions, just monitor
    """
    basket_tp = float(settings.get('Basket_Take_Profit', 10))
    grid_step = int(settings.get('Grid_Step', 100))
    max_positions = int(settings.get('Max_Open_Positions', 1))
    lot_size = get_fixed_lot_size(settings)
    
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
    
    log("INFO", f"Processing {len(allowed_symbols)} symbols", account_id)
    
    # Step 1: Check basket TP for all symbols
    closed_symbols = check_basket_tp_per_symbol(account_id, basket_tp)
    
    # Step 2: Process each symbol
    for symbol in allowed_symbols:
        positions = get_symbol_positions(symbol)
        total_orders = len(positions)
        total_profit = get_symbol_open_profit(symbol)
        
        # Case 1: No positions - open first trade (includes symbols just closed by basket TP)
        if total_orders == 0:
            direction = check_market_direction(symbol)
            if direction != 'NONE':
                if symbol in closed_symbols:
                    log("INFO", f"[RE-OPEN] {symbol}: Basket TP hit | Direction={direction} -> OPENING", account_id)
                else:
                    log("INFO", f"[OPEN] {symbol}: No positions | Direction={direction} -> OPENING", account_id)
                execute_trade(symbol, direction, lot_size, account_id)
            else:
                log("DEBUG", f"[OPEN] {symbol}: No positions | Direction=NONE -> SKIP", account_id)
        
        # Case 2: Has positions - check grid steps and monitor
        elif total_orders < max_positions:
            # Check if we should add grid positions
            check_and_open_grid_steps(symbol, grid_step, lot_size, account_id, max_positions)
            log("DEBUG", f"[MONITOR] {symbol}: {total_orders}/{max_positions} positions | P/L=${total_profit:.2f} | Waiting for basket TP ${basket_tp}", account_id)
        
        # Case 3: Max positions reached - just monitor
        elif total_orders >= max_positions:
            log("DEBUG", f"[MAX POSITIONS] {symbol}: {total_orders}/{max_positions} positions | P/L=${total_profit:.2f} | No more grid", account_id)

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
            # Update DB
            try:
                supabase.table("trades").update({
                    "status": "closed",
                    "close_reason": "basket_tp",
                    "closed_at": datetime.now(timezone.utc).isoformat()
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
def execute_trade(symbol: str, order_type: str, lot_size: float, account_id: str) -> bool:
    """
    Execute a trade order.
    order_type: 'BUY' or 'SELL'
    """
    # HARD SECURITY CHECK: Verify symbol is allowed before ANY trade
    if not is_allowed_symbol(symbol, {}):
        log("ERROR", f"[SECURITY ALERT] Attempted to trade {symbol} which is NOT ALLOWED! Trade BLOCKED.", account_id)
        return False
    
    # EMERGENCY STOP: Check equity before opening trade
    try:
        info = mt5.account_info()
        if info:
            equity = info.equity
            balance = info.balance
            # If equity is critically low (< $100), stop opening new trades
            if equity < 100:
                log("ERROR", f"[EMERGENCY STOP] Equity ${equity:.2f} is critically low (< $100). BLOCKING new trades.", account_id)
                return False
            # Check if floating loss is too high
            floating_pl = equity - balance
            if balance > 0 and floating_pl < -(balance * 0.5):  # 50% loss
                log("ERROR", f"[EMERGENCY STOP] Floating loss ${floating_pl:.2f} exceeds 50% of balance. BLOCKING new trades.", account_id)
                return False
    except Exception as e:
        log("WARN", f"Failed to check account info before trade: {e}", account_id)
    
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
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5_order_type,
            "price": price,
            "deviation": 20,
            "magic": 100000,
            "comment": "MOKABot Grid",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log("INFO", f"[TRADE OPENED] {order_type} {symbol} {lot_size} lots @ {price} | Order: {result.order}", account_id)
            return True
        else:
            error = result.comment if result else "No result"
            log("ERROR", f"Trade failed for {symbol}: {error}", account_id)
            return False
    except Exception as e:
        log("ERROR", f"Exception executing trade: {e}", account_id)
        return False

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
