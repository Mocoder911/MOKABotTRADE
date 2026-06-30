"""
MOKABotTRADE — MT5 ↔ Supabase Bridge (Strategy Framework)
==========================================================
Architecture: Executor Pattern
- Bot reads trading rules from Supabase every cycle
- No hardcoded trading logic
- All strategies, risk rules, and filters are DB-driven
- Changes in DB reflect immediately without restart

Tables used:
  - strategies: Entry/Exit/Sizing rules (JSONB)
  - risk_matrix: Per-symbol risk parameters
  - account_balance: Live account metrics
  - trades: Open positions sync
  - trade_signals: Signal audit log
  - execution_log: Trade execution log
"""

import MetaTrader5 as mt5
import time
import sys
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from supabase import create_client

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (from environment or hardcoded)
# ═══════════════════════════════════════════════════════════════════════════════
SUPABASE_URL = "https://gonfmiqwothggojdmglf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdvbmZtaXF3b3RoZ2dvamRtZ2xmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4Mjc2Nzk5NiwiZXhwIjoyMDk4MzQzOTk2fQ.MJ1T20lriV99v_uczf3n-D52ybqODBKGiXSjjW8tudI"

LOGIN = 260904217
PASSWORD = "Kikokok3@"
SERVER = "Exness-MT5Trial15"

# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE CLIENT
# ═══════════════════════════════════════════════════════════════════════════════
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# RISK MANAGER — Reads risk_matrix from DB
# ═══════════════════════════════════════════════════════════════════════════════
class RiskManager:
    """Calculates position sizes, SL/TP based on risk_matrix table"""
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_fetch = 0
    
    def fetch_risk_params(self, symbol: str, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch risk parameters for a symbol from DB"""
        # Refresh cache every 30 seconds or if forced
        now = time.time()
        if force_refresh or now - self._last_fetch > 30:
            try:
                result = supabase.table("risk_matrix").select("*").execute()
                if result.data:
                    self._cache = {row["symbol"]: row for row in result.data}
                    self._last_fetch = now
            except Exception as e:
                print(f"[RISK] Error fetching risk_matrix: {e}")
        
        return self._cache.get(symbol)
    
    def calculate_volume(self, symbol: str, balance: float, risk_rules: Dict) -> float:
        """Calculate position volume based on risk rules"""
        risk_params = self.fetch_risk_params(symbol)
        if not risk_params:
            return 0.0
        
        mode = risk_rules.get("mode", "fixed")
        max_volume = risk_rules.get("max_volume", 1.0)
        base_volume = risk_params.get("base_volume", 0.01)
        
        if mode == "risk_percent":
            risk_per_trade = risk_rules.get("risk_per_trade", 1.0)  # % of balance
            risk_amount = balance * (risk_per_trade / 100)
            sl_points = risk_params.get("sl_points", 100)
            
            # Calculate volume based on risk (simplified)
            # In real implementation, need tick_value, tick_size
            tick_value = self._get_tick_value(symbol)
            if tick_value and sl_points > 0:
                risk_per_lot = sl_points * tick_value
                if risk_per_lot > 0:
                    volume = risk_amount / risk_per_lot
                    return min(volume, max_volume)
        
        # Default: use base volume from risk_matrix
        return min(base_volume, max_volume)
    
    def get_sl_tp(self, symbol: str, trade_type: str, entry_price: float) -> tuple:
        """Get SL and TP prices based on risk_matrix"""
        risk_params = self.fetch_risk_params(symbol)
        if not risk_params:
            return (0.0, 0.0)
        
        sl_points = risk_params.get("sl_points", 0)
        tp_points = risk_params.get("tp_points", 0)
        
        # Get point value for symbol
        point = self._get_point(symbol)
        if not point:
            return (0.0, 0.0)
        
        if trade_type == "BUY":
            sl = entry_price - (sl_points * point)
            tp = entry_price + (tp_points * point)
        else:  # SELL
            sl = entry_price + (sl_points * point)
            tp = entry_price - (tp_points * point)
        
        return (round(sl, 5), round(tp, 5))
    
    def _get_point(self, symbol: str) -> Optional[float]:
        """Get point value for symbol"""
        try:
            info = mt5.symbol_info(symbol)
            return info.point if info else None
        except:
            return None
    
    def _get_tick_value(self, symbol: str) -> Optional[float]:
        """Get tick value for symbol"""
        try:
            info = mt5.symbol_info(symbol)
            return info.trade_tick_value if info else None
        except:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL EVALUATOR — Evaluates market conditions against strategy rules
# ═══════════════════════════════════════════════════════════════════════════════
class SignalEvaluator:
    """Evaluates entry/exit conditions from strategy rules"""
    
    def __init__(self):
        self._indicator_cache: Dict[str, Dict] = {}
    
    def evaluate_entry(self, symbol: str, entry_rules: Dict) -> Optional[str]:
        """
        Evaluate entry conditions. Returns 'BUY', 'SELL', or None.
        
        entry_rules format:
        {
            "indicators": [
                {"name": "RSI", "condition": "less_than", "value": 30},
                {"name": "MACD", "condition": "crosses_above", "compare": "signal"}
            ],
            "pattern": "bullish_engulfing"  # optional
        }
        """
        indicators = entry_rules.get("indicators", [])
        if not indicators:
            return None
        
        results = []
        for rule in indicators:
            result = self._check_indicator(symbol, rule)
            if result is not None:
                results.append(result)
        
        # All conditions must agree on direction
        if not results:
            return None
        
        buy_count = results.count("BUY")
        sell_count = results.count("SELL")
        
        # Require majority agreement
        if buy_count > sell_count and buy_count >= len(indicators) / 2:
            return "BUY"
        elif sell_count > buy_count and sell_count >= len(indicators) / 2:
            return "SELL"
        
        return None
    
    def evaluate_exit(self, symbol: str, position, exit_rules: Dict) -> Optional[str]:
        """
        Evaluate exit conditions. Returns 'CLOSE' or None.
        """
        # Check if exit_rules says to use risk_matrix (handled elsewhere)
        if exit_rules.get("take_profit") == "use_risk_matrix":
            # SL/TP handled by MT5 directly
            return None
        
        # Check trailing stop
        if exit_rules.get("trailing"):
            trailing_result = self._check_trailing(symbol, position, exit_rules)
            if trailing_result:
                return trailing_result
        
        return None
    
    def _check_indicator(self, symbol: str, rule: Dict) -> Optional[str]:
        """Check a single indicator rule"""
        name = rule.get("name", "").upper()
        condition = rule.get("condition", "")
        value = rule.get("value")
        
        # Get indicator value (simplified - in production, use TA-Lib or custom)
        indicator_value = self._get_indicator_value(symbol, name)
        if indicator_value is None:
            return None
        
        # Evaluate condition
        if condition == "less_than":
            if indicator_value < value:
                return "BUY"  # Oversold = buy signal
        elif condition == "greater_than":
            if indicator_value > value:
                return "SELL"  # Overbought = sell signal
        elif condition == "crosses_above":
            # Would need historical data for proper cross detection
            pass
        elif condition == "crosses_below":
            pass
        
        return None
    
    def _get_indicator_value(self, symbol: str, indicator: str) -> Optional[float]:
        """
        Get indicator value. This is a placeholder for actual indicator calculation.
        In production, use TA-Lib, pandas_ta, or custom calculations.
        """
        # Fetch recent candles
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50)
        if rates is None or len(rates) < 20:
            return None
        
        if indicator == "RSI":
            return self._calculate_rsi(rates)
        elif indicator == "MACD":
            return self._calculate_macd(rates)
        
        return None
    
    def _calculate_rsi(self, rates, period: int = 14) -> float:
        """Calculate RSI from rates"""
        closes = [r['close'] for r in rates]
        if len(closes) < period + 1:
            return 50.0  # Neutral default
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, rates) -> float:
        """Calculate MACD (simplified)"""
        # This is a placeholder - proper implementation needs EMA calculation
        return 0.0
    
    def _check_trailing(self, symbol: str, position, exit_rules: Dict) -> Optional[str]:
        """Check trailing stop conditions"""
        # Simplified trailing stop logic
        trail_points = exit_rules.get("trail_points", 50)
        current_price = mt5.symbol_info_tick(symbol)
        if not current_price:
            return None
        
        if position.type == mt5.POSITION_TYPE_BUY:
            # For buy, trail below current price
            trail_level = current_price.bid - (trail_points * self._get_point(symbol))
            if position.sl < trail_level:
                return "MODIFY_SL"
        else:
            # For sell, trail above current price
            trail_level = current_price.ask + (trail_points * self._get_point(symbol))
            if position.sl > trail_level or position.sl == 0:
                return "MODIFY_SL"
        
        return None
    
    def _get_point(self, symbol: str) -> float:
        info = mt5.symbol_info(symbol)
        return info.point if info else 0.0001


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY ENGINE — Reads strategies from DB and orchestrates execution
# ═══════════════════════════════════════════════════════════════════════════════
class StrategyEngine:
    """Main engine that reads strategies from DB and executes them"""
    
    def __init__(self):
        self.risk_manager = RiskManager()
        self.signal_evaluator = SignalEvaluator()
        self._strategies_cache: List[Dict] = []
        self._last_strategy_fetch = 0
    
    def fetch_active_strategies(self, force_refresh: bool = False) -> List[Dict]:
        """Fetch active strategies from DB"""
        now = time.time()
        if force_refresh or now - self._last_strategy_fetch > 30:  # Refresh every 30s
            try:
                result = supabase.table("strategies") \
                    .select("*") \
                    .eq("is_active", True) \
                    .order("priority", desc=True) \
                    .execute()
                
                if result.data:
                    self._strategies_cache = result.data
                    self._last_strategy_fetch = now
                    print(f"[ENGINE] Loaded {len(result.data)} active strategies")
                else:
                    self._strategies_cache = []
            except Exception as e:
                print(f"[ENGINE] Error fetching strategies: {e}")
        
        return self._strategies_cache
    
    def process_cycle(self, bot_active: bool):
        """Process one cycle: evaluate strategies and execute if conditions met"""
        if not bot_active:
            return
        
        strategies = self.fetch_active_strategies()
        if not strategies:
            return
        
        # Get account info for position sizing
        account_info = mt5.account_info()
        if not account_info:
            return
        
        balance = account_info.balance
        
        # Get existing positions
        positions = mt5.positions_get()
        open_symbols = {p.symbol for p in positions} if positions else set()
        
        for strategy in strategies:
            symbol = strategy.get("symbol")
            if not symbol:
                continue
            
            entry_rules = strategy.get("entry_rules", {})
            exit_rules = strategy.get("exit_rules", {})
            sizing_rules = strategy.get("sizing_rules", {})
            filters = strategy.get("filters", {})
            
            # Check filters first
            if not self._check_filters(symbol, filters):
                continue
            
            # Check if we already have a position for this symbol
            if symbol in open_symbols:
                # Evaluate exit conditions
                position = next((p for p in positions if p.symbol == symbol), None)
                if position:
                    self._evaluate_exit(strategy, position, exit_rules)
            else:
                # Evaluate entry conditions
                signal = self.signal_evaluator.evaluate_entry(symbol, entry_rules)
                if signal:
                    self._execute_entry(strategy, symbol, signal, sizing_rules, balance)
    
    def _check_filters(self, symbol: str, filters: Dict) -> bool:
        """Check if symbol passes filters (spread, session, etc.)"""
        # Check max spread
        max_spread = filters.get("max_spread_points")
        if max_spread:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                spread = int((tick.ask - tick.bid) / mt5.symbol_info(symbol).point)
                if spread > max_spread:
                    return False
        
        # Check session (simplified)
        sessions = filters.get("sessions", [])
        if sessions:
            current_hour = datetime.now().hour
            # Map sessions to hours (UTC)
            session_hours = {
                "sydney": (22, 7),
                "tokyo": (0, 9),
                "london": (7, 16),
                "new_york": (12, 21),
            }
            in_session = False
            for session in sessions:
                if session in session_hours:
                    start, end = session_hours[session]
                    if start <= current_hour < end:
                        in_session = True
                        break
            if not in_session:
                return False
        
        return True
    
    def _execute_entry(self, strategy: Dict, symbol: str, signal: str, 
                       sizing_rules: Dict, balance: float):
        """Execute entry order"""
        strategy_id = strategy.get("id")
        strategy_name = strategy.get("name")
        
        # Calculate volume
        volume = self.risk_manager.calculate_volume(symbol, balance, sizing_rules)
        if volume <= 0:
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", 
                           "SKIPPED", "Invalid volume")
            return
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return
        
        price = tick.ask if signal == "BUY" else tick.bid
        
        # Get SL/TP from risk_matrix
        sl, tp = self.risk_manager.get_sl_tp(symbol, signal, price)
        
        # Prepare order
        order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,  # Max slippage in points
            "magic": 100000 + hash(strategy_id) % 100000,  # Unique per strategy
            "comment": f"MOKA:{strategy_name[:10]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Execute order
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTE] {signal} {symbol} @ {price} | Vol: {volume} | SL: {sl} | TP: {tp}")
            self._log_execution(strategy_id, result.order, "OPEN", symbol, volume, price, sl, tp, 
                              {"retcode": result.retcode, "deal": result.deal})
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "EXECUTED", f"Ticket: {result.order}")
        else:
            error = result.comment if result else "No result"
            print(f"[EXECUTE FAILED] {signal} {symbol}: {error}")
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "FAILED", error)
    
    def _evaluate_exit(self, strategy: Dict, position, exit_rules: Dict):
        """Evaluate and execute exit conditions"""
        strategy_id = strategy.get("id")
        signal = self.signal_evaluator.evaluate_exit(strategy.get("symbol"), position, exit_rules)
        
        if signal == "CLOSE":
            self._close_position(strategy_id, position)
        elif signal == "MODIFY_SL":
            self._modify_position(strategy_id, position, exit_rules)
    
    def _close_position(self, strategy_id: str, position):
        """Close an open position"""
        tick = mt5.symbol_info_tick(position.symbol)
        if not tick:
            return
        
        close_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": position.ticket,
            "price": close_price,
            "deviation": 20,
            "magic": 100000 + hash(strategy_id) % 100000,
            "comment": "MOKA:EXIT",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[CLOSE] {position.symbol} ticket {position.ticket} @ {close_price}")
            self._log_execution(strategy_id, position.ticket, "CLOSE", position.symbol, 
                              position.volume, close_price, None, None, {"retcode": result.retcode})
    
    def _modify_position(self, strategy_id: str, position, exit_rules: Dict):
        """Modify position SL/TP"""
        # Get new SL based on trailing
        trail_points = exit_rules.get("trail_points", 50)
        point = self.risk_manager._get_point(position.symbol)
        tick = mt5.symbol_info_tick(position.symbol)
        if not tick:
            return
        
        new_sl = position.sl
        new_tp = position.tp
        
        if position.type == mt5.POSITION_TYPE_BUY:
            new_sl = tick.bid - (trail_points * point)
        else:
            new_sl = tick.ask + (trail_points * point)
        
        # Only modify if new SL is better
        if position.type == mt5.POSITION_TYPE_BUY and new_sl <= position.sl:
            return
        if position.type == mt5.POSITION_TYPE_SELL and (new_sl >= position.sl or position.sl == 0):
            if position.sl != 0 and new_sl >= position.sl:
                return
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position.ticket,
            "sl": round(new_sl, 5),
            "tp": round(new_tp, 5),
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[MODIFY] {position.symbol} ticket {position.ticket} | New SL: {new_sl}")
            self._log_execution(strategy_id, position.ticket, "MODIFY", position.symbol,
                              position.volume, None, new_sl, new_tp, {"retcode": result.retcode})
    
    def _log_signal(self, strategy_id: str, symbol: str, signal_type: str, 
                   action_taken: str, reason: str):
        """Log signal to trade_signals table"""
        try:
            supabase.table("trade_signals").insert({
                "strategy_id": strategy_id,
                "symbol": symbol,
                "signal_type": signal_type,
                "signal_data": {},
                "action_taken": action_taken,
                "action_reason": reason,
            }).execute()
        except Exception as e:
            print(f"[LOG] Signal log error: {e}")
    
    def _log_execution(self, strategy_id: str, ticket: str, action: str, symbol: str,
                      volume: float, price: float, sl: float, tp: float, result: Dict):
        """Log execution to execution_log table"""
        try:
            supabase.table("execution_log").insert({
                "strategy_id": strategy_id,
                "ticket": str(ticket),
                "action": action,
                "symbol": symbol,
                "volume": volume,
                "price": price,
                "sl": sl,
                "tp": tp,
                "result": result,
            }).execute()
        except Exception as e:
            print(f"[LOG] Execution log error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SYNC — Syncs account balance and trades to Supabase
# ═══════════════════════════════════════════════════════════════════════════════
def get_user_id(mt5_account_id: str) -> Optional[str]:
    """Get user_id from profiles table"""
    try:
        result = supabase.table("profiles") \
            .select("id") \
            .eq("mt5_account_id", mt5_account_id) \
            .maybe_single() \
            .execute()
        return result.data["id"] if result.data else None
    except Exception as e:
        print(f"[SYNC] User ID error: {e}")
        return None


def sync_account_balance(mt5_account_id: str):
    """Sync account balance to Supabase"""
    info = mt5.account_info()
    if not info:
        return
    
    user_id = get_user_id(mt5_account_id)
    if not user_id:
        return
    
    try:
        supabase.table("account_balance").upsert({
            "user_id": user_id,
            "balance": info.balance,
            "equity": info.equity,
            "updated_at": "now()",
        }, on_conflict="user_id").execute()
    except Exception as e:
        print(f"[SYNC] Balance error: {e}")


def sync_trades(mt5_account_id: str):
    """Sync open trades to Supabase"""
    positions = mt5.positions_get()
    if positions is None:
        positions = []
    
    current_tickets = set()
    
    for pos in positions:
        ticket = str(pos.ticket)
        current_tickets.add(ticket)
        
        try:
            supabase.table("trades").upsert({
                "ticket": ticket,
                "account_id": mt5_account_id,
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
            }, on_conflict="ticket").execute()
        except Exception as e:
            print(f"[SYNC] Trade error for {ticket}: {e}")
    
    # Mark closed trades
    try:
        db_trades = supabase.table("trades") \
            .select("ticket") \
            .eq("account_id", mt5_account_id) \
            .eq("status", "open") \
            .execute()
        
        if db_trades.data:
            for t in db_trades.data:
                if t["ticket"] not in current_tickets:
                    supabase.table("trades") \
                        .update({"status": "closed"}) \
                        .eq("ticket", t["ticket"]) \
                        .execute()
    except Exception as e:
        print(f"[SYNC] Close check error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# BOT STATUS CHECK
# ═══════════════════════════════════════════════════════════════════════════════
def get_bot_status(mt5_account_id: str) -> bool:
    """Check if bot is active from profiles table"""
    try:
        result = supabase.table("profiles") \
            .select("bot_active") \
            .eq("mt5_account_id", mt5_account_id) \
            .maybe_single() \
            .execute()
        return result.data.get("bot_active", False) if result.data else False
    except Exception as e:
        print(f"[STATUS] Error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("  MOKABotTRADE — Strategy Framework Bridge")
print("  Architecture: Executor Pattern (DB-driven rules)")
print("=" * 60)

# Connect to MT5
if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
    print(f"[ERROR] MT5 connection failed: {mt5.last_error()}")
    sys.exit(1)

account_info = mt5.account_info()
if not account_info:
    print("[ERROR] Failed to get account info")
    mt5.shutdown()
    sys.exit(1)

print(f"[OK] Connected to MT5")
print(f"     Account: {account_info.login}")
print(f"     Server:  {account_info.server}")
print(f"     Balance: ${account_info.balance:.2f}")
print("=" * 60)

MT5_ACCOUNT_ID = str(account_info.login)

# Initialize strategy engine
engine = StrategyEngine()

print("\n[BRIDGE] Starting execution loop (every 10 seconds)...")
print("[INFO] Data sync: ALWAYS ON")
print("[INFO] Strategy execution: Controlled by bot_active toggle")
print("[INFO] Strategies are fetched from DB every cycle\n")

cycle = 0
while True:
    try:
        cycle += 1
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # ALWAYS sync data
        print(f"--- Cycle {cycle} @ {timestamp} ---")
        sync_account_balance(MT5_ACCOUNT_ID)
        sync_trades(MT5_ACCOUNT_ID)
        
        # Check bot status
        bot_active = get_bot_status(MT5_ACCOUNT_ID)
        
        if bot_active:
            print(f"[BOT] ▶ RUNNING — Executing strategies...")
            engine.process_cycle(bot_active=True)
        else:
            print(f"[BOT] ⏸  STANDBY — Monitoring only")
        
        print(f"--- Next cycle in 10s ---\n")
        time.sleep(10)
    
    except KeyboardInterrupt:
        print("\n[BRIDGE] Stopping...")
        mt5.shutdown()
        print("[BRIDGE] Done.")
        break
    
    except Exception as e:
        print(f"[FATAL] {e}")
        time.sleep(5)
