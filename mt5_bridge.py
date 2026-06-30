"""
MOKABotTRADE — MT5 ↔ Supabase Bridge (Generic Strategy Framework)
==================================================================
Architecture: Generic Rule Executor
- ALL trading logic is defined in Supabase JSONB
- No hardcoded indicators or conditions in Python
- Uses pandas-ta for dynamic indicator calculation
- Any indicator change in DB = immediate behavior change

Tables used:
  - strategies: Entry/Exit/Sizing rules (JSONB)
  - risk_matrix: Per-symbol risk parameters
  - account_balance: Live account metrics
  - trades: Open positions sync
  - trade_signals: Signal audit log
  - execution_log: Trade execution log

JSONB Rule Format:
  entry_rules: {
    "conditions": [
      {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30},
      {"indicator": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_above", "compare_to": "signal"}
    ],
    "logic": "AND"  // or "OR"
  }
"""

import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import time
import sys
import operator
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from supabase import create_client

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
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
# OPERATOR MAP — Maps JSON operators to Python functions
# ═══════════════════════════════════════════════════════════════════════════════
OPERATORS: Dict[str, Callable] = {
    "lt": operator.lt,           # less than
    "gt": operator.gt,           # greater than
    "lte": operator.le,          # less than or equal
    "gte": operator.ge,          # greater than or equal
    "eq": operator.eq,           # equal
    "neq": operator.ne,          # not equal
    "crosses_above": None,       # special handling
    "crosses_below": None,       # special handling
}


# ═══════════════════════════════════════════════════════════════════════════════
# INDICATOR CALCULATOR — Generic, uses pandas-ta
# ═══════════════════════════════════════════════════════════════════════════════
class IndicatorCalculator:
    """
    Generic indicator calculator using pandas-ta.
    Calculates ANY indicator by name + params from JSONB.
    """
    
    # Timeframe mapping
    TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
    }
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Dict[str, float] = {}
    
    def get_dataframe(self, symbol: str, timeframe: str = "M15", bars: int = 200) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data and convert to pandas DataFrame"""
        cache_key = f"{symbol}_{timeframe}"
        now = time.time()
        
        # Cache for 5 seconds
        if cache_key in self._cache and now - self._cache_time.get(cache_key, 0) < 5:
            return self._cache[cache_key]
        
        tf = self.TIMEFRAMES.get(timeframe, mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        
        if rates is None or len(rates) == 0:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        self._cache[cache_key] = df
        self._cache_time[cache_key] = now
        return df
    
    def calculate(self, symbol: str, indicator_name: str, params: Dict, timeframe: str = "M15") -> Optional[Any]:
        """
        Calculate ANY indicator dynamically.
        
        indicator_name: lowercase name (rsi, macd, bbands, sma, ema, price, etc.)
        params: parameters dict from JSONB
        
        Returns the indicator value(s) or None.
        """
        df = self.get_dataframe(symbol, timeframe)
        if df is None or len(df) < 50:
            return None
        
        # Special case: "price" returns current close price
        if indicator_name.lower() == "price":
            return {"price": df['close'].iloc[-1]}
        
        # Convert indicator name to pandas-ta function name
        indicator_lower = indicator_name.lower().replace(" ", "").replace("_", "")
        
        try:
            # Use pandas-ta's strategy method to add indicator
            # pandas-ta supports 100+ indicators dynamically
            result = self._call_pandas_ta(df, indicator_lower, params)
            return result
        except Exception as e:
            print(f"[INDICATOR] Error calculating {indicator_name}: {e}")
            return None
    
    def _call_pandas_ta(self, df: pd.DataFrame, indicator: str, params: Dict) -> Optional[Any]:
        """
        Dynamically call pandas-ta indicator.
        Returns the latest value(s) of the indicator.
        """
        # Map common indicator names to pandas-ta function names
        indicator_map = {
            "rsi": "rsi",
            "macd": "macd",
            "sma": "sma",
            "ema": "ema",
            "wma": "wma",
            "bbands": "bbands",
            "stoch": "stoch",
            "atr": "atr",
            "adx": "adx",
            "cci": "cci",
            "willr": "willr",
            "roc": "roc",
            "mom": "mom",
            "dmi": "dmi",
            "aroon": "aroon",
            "supertrend": "supertrend",
            "psar": "psar",
            "vwap": "vwap",
            "obv": "obv",
            "mfi": "mfi",
            "keltner": "keltner_channel",
            "donchian": "donchian",
            "pivot": "pivot_points",
        }
        
        ta_func_name = indicator_map.get(indicator, indicator)
        
        # Get the pandas-ta function
        ta_func = getattr(df.ta, ta_func_name, None)
        if ta_func is None:
            # Try the strategy approach
            return self._use_strategy(df, indicator, params)
        
        # Call the function with params
        result = ta_func(**params, append=True)
        
        # Get the last value(s)
        if result is not None:
            # Find columns that were added
            new_cols = [c for c in df.columns if ta_func_name.upper() in str(c).upper()]
            if new_cols:
                return {col: df[col].iloc[-1] for col in new_cols}
        
        return None
    
    def _use_strategy(self, df: pd.DataFrame, indicator: str, params: Dict) -> Optional[Any]:
        """Use pandas-ta strategy for complex indicators"""
        try:
            # Create a custom strategy with just this indicator
            strategy = ta.Strategy(
                name=f"dynamic_{indicator}",
                ta=[{"kind": indicator, **params}]
            )
            df.ta.strategy(strategy)
            
            # Return last values of newly added columns
            original_cols = {'open', 'high', 'low', 'close', 'volume', 'tick_volume', 'spread', 'real_volume'}
            new_cols = [c for c in df.columns if c not in original_cols]
            
            if new_cols:
                return {col: df[col].iloc[-1] for col in new_cols}
        except Exception as e:
            print(f"[INDICATOR] Strategy error for {indicator}: {e}")
        
        return None
    
    def get_previous_value(self, symbol: str, indicator_name: str, params: Dict, timeframe: str = "M15") -> Optional[Any]:
        """Get the previous candle's indicator value (for cross detection)"""
        df = self.get_dataframe(symbol, timeframe)
        if df is None or len(df) < 50:
            return None
        
        indicator_lower = indicator_name.lower().replace(" ", "").replace("_", "")
        
        try:
            ta_func = getattr(df.ta, indicator_lower, None)
            if ta_func:
                ta_func(**params, append=True)
                new_cols = [c for c in df.columns if indicator_lower.upper() in str(c).upper()]
                if new_cols and len(df) >= 2:
                    return {col: df[col].iloc[-2] for col in new_cols}
        except:
            pass
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# GENERIC SIGNAL EVALUATOR — Reads rules from JSONB, no hardcoded logic
# ═══════════════════════════════════════════════════════════════════════════════
class GenericSignalEvaluator:
    """
    Evaluates ANY trading rule defined in JSONB.
    No hardcoded indicators or conditions.
    """
    
    def __init__(self, calculator: IndicatorCalculator):
        self.calc = calculator
    
    def evaluate(self, symbol: str, rules: Dict) -> Optional[str]:
        """
        Evaluate rules and return signal: 'BUY', 'SELL', or None.
        
        rules format (from JSONB):
        {
            "conditions": [
                {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30},
                {"indicator": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_above", "compare_to": "signal"}
            ],
            "logic": "AND"  // or "OR"
        }
        """
        conditions = rules.get("conditions", [])
        logic = rules.get("logic", "AND").upper()
        timeframe = rules.get("timeframe", "M15")
        
        if not conditions:
            return None
        
        results = []
        for condition in conditions:
            result = self._evaluate_condition(symbol, condition, timeframe)
            if result is not None:
                results.append(result)
        
        if not results:
            return None
        
        # Apply logic (AND/OR)
        if logic == "AND":
            # All conditions must agree
            buy_count = results.count("BUY")
            sell_count = results.count("SELL")
            
            if buy_count == len(results):
                return "BUY"
            elif sell_count == len(results):
                return "SELL"
            return None
        else:  # OR
            if "BUY" in results:
                return "BUY"
            if "SELL" in results:
                return "SELL"
            return None
    
    def _evaluate_condition(self, symbol: str, condition: Dict, timeframe: str) -> Optional[str]:
        """
        Evaluate a single condition from JSONB.
        Returns 'BUY', 'SELL', or None.
        
        Supports:
        - Simple: {"indicator": "rsi", "params": {"length": 14}, "operator": "lt", "value": 30}
        - Cross: {"indicator": "macd", "params": {...}, "operator": "crosses_above", "compare_to": "signal"}
        - Compare indicators: {"indicator": "price", "operator": "gt", "compare_indicator": "ema", "compare_params": {"length": 50}}
        """
        indicator = condition.get("indicator", "")
        params = condition.get("params", {})
        op = condition.get("operator", "")
        value = condition.get("value")
        compare_to = condition.get("compare_to")
        compare_indicator = condition.get("compare_indicator")
        compare_params = condition.get("compare_params", {})
        
        # Calculate main indicator values
        current = self.calc.calculate(symbol, indicator, params, timeframe)
        if current is None:
            return None
        
        # Handle cross detection
        if op in ("crosses_above", "crosses_below"):
            previous = self.calc.get_previous_value(symbol, indicator, params, timeframe)
            if previous is None:
                return None
            return self._evaluate_cross(current, previous, compare_to, op)
        
        # Handle comparison against another indicator
        if compare_indicator:
            other = self.calc.calculate(symbol, compare_indicator, compare_params, timeframe)
            if other is None:
                return None
            # Get first value from each
            main_value = list(current.values())[0] if current else None
            other_value = list(other.values())[0] if other else None
            if main_value is None or other_value is None:
                return None
            
            op_func = OPERATORS.get(op)
            if op_func and op_func(main_value, other_value):
                # Price > indicator = bullish = BUY
                # Price < indicator = bearish = SELL
                return "BUY" if op in ("gt", "gte") else "SELL"
            return None
        
        # Handle comparison operators (against fixed value)
        return self._evaluate_comparison(current, op, value, compare_to)
    
    def _evaluate_cross(self, current: Dict, previous: Dict, compare_to: str, op: str) -> Optional[str]:
        """Evaluate cross conditions"""
        # Find the main line and compare line
        main_key = None
        compare_key = None
        
        for key in current.keys():
            key_lower = key.lower()
            if compare_to and compare_to.lower() in key_lower:
                compare_key = key
            elif main_key is None:
                main_key = key
        
        if main_key is None or compare_key is None:
            # Fallback: use first two keys
            keys = list(current.keys())
            if len(keys) >= 2:
                main_key = keys[0]
                compare_key = keys[1]
            else:
                return None
        
        curr_main = current[main_key]
        curr_compare = current[compare_key]
        prev_main = previous.get(main_key, curr_main)
        prev_compare = previous.get(compare_key, curr_compare)
        
        if op == "crosses_above":
            # Main was below compare, now above
            if prev_main <= prev_compare and curr_main > curr_compare:
                return "BUY"
        elif op == "crosses_below":
            # Main was above compare, now below
            if prev_main >= prev_compare and curr_main < curr_compare:
                return "SELL"
        
        return None
    
    def _evaluate_comparison(self, current: Dict, op: str, value: Any, compare_to: str) -> Optional[str]:
        """Evaluate comparison operators"""
        op_func = OPERATORS.get(op)
        if op_func is None:
            return None
        
        # Find the value to compare
        if compare_to:
            # Compare two indicator lines
            compare_value = None
            for key in current.keys():
                if compare_to.lower() in key.lower():
                    compare_value = current[key]
                    break
            if compare_value is None:
                return None
            
            # Get the main value (first non-compare key)
            main_value = None
            for key in current.keys():
                if compare_to.lower() not in key.lower():
                    main_value = current[key]
                    break
            
            if main_value is None:
                return None
            
            if op_func(main_value, compare_value):
                return "BUY" if op in ("lt", "lte", "crosses_below") else "SELL"
        else:
            # Compare against fixed value
            main_value = list(current.values())[0] if current else None
            if main_value is None:
                return None
            
            if op_func(main_value, value):
                # Determine direction based on operator
                if op in ("lt", "lte"):
                    return "BUY"  # Oversold
                elif op in ("gt", "gte"):
                    return "SELL"  # Overbought
                elif op == "eq":
                    return "BUY" if main_value == value else None
        
        return None


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
    
    def calculate_volume(self, symbol: str, balance: float, sizing_rules: Dict) -> float:
        """Calculate position volume based on sizing rules from JSONB"""
        risk_params = self.fetch_risk_params(symbol)
        if not risk_params:
            return 0.0
        
        mode = sizing_rules.get("mode", "fixed")
        max_volume = sizing_rules.get("max_volume", 1.0)
        base_volume = risk_params.get("base_volume", 0.01)
        
        if mode == "risk_percent":
            risk_per_trade = sizing_rules.get("risk_per_trade", 1.0)
            risk_amount = balance * (risk_per_trade / 100)
            sl_points = risk_params.get("sl_points", 100)
            
            tick_value = self._get_tick_value(symbol)
            if tick_value and sl_points > 0:
                risk_per_lot = sl_points * tick_value
                if risk_per_lot > 0:
                    volume = risk_amount / risk_per_lot
                    # Round to lot step
                    info = mt5.symbol_info(symbol)
                    if info:
                        step = info.volume_step
                        volume = round(volume / step) * step
                    return min(max(volume, 0.01), max_volume)
        
        return min(base_volume, max_volume)
    
    def get_sl_tp(self, symbol: str, trade_type: str, entry_price: float) -> tuple:
        """Get SL and TP prices based on risk_matrix"""
        risk_params = self.fetch_risk_params(symbol)
        if not risk_params:
            return (0.0, 0.0)
        
        sl_points = risk_params.get("sl_points", 0)
        tp_points = risk_params.get("tp_points", 0)
        
        point = self._get_point(symbol)
        if not point:
            return (0.0, 0.0)
        
        if trade_type == "BUY":
            sl = entry_price - (sl_points * point)
            tp = entry_price + (tp_points * point)
        else:
            sl = entry_price + (sl_points * point)
            tp = entry_price - (tp_points * point)
        
        return (round(sl, 5), round(tp, 5))
    
    def _get_point(self, symbol: str) -> Optional[float]:
        try:
            info = mt5.symbol_info(symbol)
            return info.point if info else None
        except:
            return None
    
    def _get_tick_value(self, symbol: str) -> Optional[float]:
        try:
            info = mt5.symbol_info(symbol)
            return info.trade_tick_value if info else None
        except:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY ENGINE — Orchestrates everything
# ═══════════════════════════════════════════════════════════════════════════════
class StrategyEngine:
    """Main engine: reads strategies from DB, evaluates, executes"""
    
    def __init__(self):
        self.calculator = IndicatorCalculator()
        self.evaluator = GenericSignalEvaluator(self.calculator)
        self.risk_manager = RiskManager()
        self._strategies_cache: List[Dict] = []
        self._last_strategy_fetch = 0
    
    def fetch_active_strategies(self, force_refresh: bool = False) -> List[Dict]:
        """Fetch active strategies from DB"""
        now = time.time()
        if force_refresh or now - self._last_strategy_fetch > 30:
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
                    for s in result.data:
                        print(f"         - {s['name']}: {s['symbol']} | Entry: {json.dumps(s.get('entry_rules', {}))[:50]}...")
                else:
                    self._strategies_cache = []
            except Exception as e:
                print(f"[ENGINE] Error fetching strategies: {e}")
        
        return self._strategies_cache
    
    def process_cycle(self, bot_active: bool):
        """Process one cycle"""
        if not bot_active:
            return
        
        strategies = self.fetch_active_strategies()
        if not strategies:
            return
        
        account_info = mt5.account_info()
        if not account_info:
            return
        
        balance = account_info.balance
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
            
            # Check filters
            if not self._check_filters(symbol, filters):
                continue
            
            # Check existing positions
            if symbol in open_symbols:
                position = next((p for p in positions if p.symbol == symbol), None)
                if position:
                    self._evaluate_exit(strategy, position, exit_rules)
            else:
                # Evaluate entry using GENERIC evaluator
                signal = self.evaluator.evaluate(symbol, entry_rules)
                if signal:
                    self._execute_entry(strategy, symbol, signal, sizing_rules, balance)
    
    def _check_filters(self, symbol: str, filters: Dict) -> bool:
        """Check filters from JSONB"""
        # Max spread
        max_spread = filters.get("max_spread_points")
        if max_spread:
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick and info:
                spread = int((tick.ask - tick.bid) / info.point)
                if spread > max_spread:
                    return False
        
        # Sessions
        sessions = filters.get("sessions", [])
        if sessions:
            current_hour = datetime.utcnow().hour
            session_hours = {
                "sydney": (22, 7), "tokyo": (0, 9),
                "london": (7, 16), "new_york": (12, 21),
            }
            in_session = any(
                start <= current_hour < end
                for s in sessions if s in session_hours
                for start, end in [session_hours[s]]
            )
            if not in_session:
                return False
        
        return True
    
    def _execute_entry(self, strategy: Dict, symbol: str, signal: str,
                       sizing_rules: Dict, balance: float):
        """Execute entry order (or simulate if dry_run=True)"""
        strategy_id = strategy.get("id")
        strategy_name = strategy.get("name")
        dry_run = strategy.get("dry_run", True)  # Default to dry_run=True for safety
            
        volume = self.risk_manager.calculate_volume(symbol, balance, sizing_rules)
        if volume <= 0:
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "SKIPPED", "Invalid volume")
            return
            
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return
            
        price = tick.ask if signal == "BUY" else tick.bid
        sl, tp = self.risk_manager.get_sl_tp(symbol, signal, price)
            
        # ─── DRY RUN MODE: Simulate without executing ──────────────────────
        if dry_run:
            print(f"[DRY RUN] {signal} {symbol} @ {price} | Vol: {volume} | SL: {sl} | TP: {tp}")
            self._log_execution(
                strategy_id, 
                f"SIM_{int(time.time())}",  # Fake ticket
                "SIMULATED", 
                symbol, 
                volume, 
                price, 
                sl, 
                tp,
                {"mode": "dry_run", "signal": signal},
                is_dry_run=True
            )
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "SIMULATED", "Dry run - no real order")
            return
            
        # ─── LIVE MODE: Execute real order ─────────────────────────────────
        order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 100000 + hash(strategy_id) % 100000,
            "comment": f"MOKA:{strategy_name[:10]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
            
        result = mt5.order_send(request)
            
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTE] {signal} {symbol} @ {price} | Vol: {volume} | SL: {sl} | TP: {tp}")
            self._log_execution(strategy_id, result.order, "OPEN", symbol, volume, price, sl, tp,
                              {"retcode": result.retcode}, is_dry_run=False)
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "EXECUTED", f"Ticket: {result.order}")
        else:
            error = result.comment if result else "No result"
            print(f"[EXECUTE FAILED] {signal} {symbol}: {error}")
            self._log_signal(strategy_id, symbol, f"ENTRY_{signal}", "FAILED", error)
    
    def _evaluate_exit(self, strategy: Dict, position, exit_rules: Dict):
        """Evaluate exit — currently relies on SL/TP set at entry"""
        # Exit rules are handled by MT5 SL/TP
        # Additional exit logic can be added via JSONB here
        pass
    
    def _log_signal(self, strategy_id: str, symbol: str, signal_type: str,
                   action_taken: str, reason: str):
        """Log to trade_signals"""
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
            print(f"[LOG] Signal error: {e}")
    
    def _log_execution(self, strategy_id: str, ticket: str, action: str, symbol: str,
                      volume: float, price: float, sl: float, tp: float, result: Dict,
                      is_dry_run: bool = False):
        """Log to execution_log"""
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
                "is_dry_run": is_dry_run,
            }).execute()
        except Exception as e:
            print(f"[LOG] Execution error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA SYNC
# ═══════════════════════════════════════════════════════════════════════════════
def get_user_id(mt5_account_id: str) -> Optional[str]:
    try:
        result = supabase.table("profiles").select("id").eq("mt5_account_id", mt5_account_id).maybe_single().execute()
        return result.data["id"] if result.data else None
    except:
        return None

def sync_account_balance(mt5_account_id: str):
    info = mt5.account_info()
    if not info:
        return
    user_id = get_user_id(mt5_account_id)
    if not user_id:
        return
    try:
        supabase.table("account_balance").upsert({
            "user_id": user_id, "balance": info.balance, "equity": info.equity, "updated_at": "now()",
        }, on_conflict="user_id").execute()
    except:
        pass

def sync_trades(mt5_account_id: str):
    positions = mt5.positions_get() or []
    current_tickets = set()
    for pos in positions:
        ticket = str(pos.ticket)
        current_tickets.add(ticket)
        try:
            supabase.table("trades").upsert({
                "ticket": ticket, "account_id": mt5_account_id, "symbol": pos.symbol,
                "type": "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": pos.volume, "entry": pos.price_open, "sl": pos.sl, "tp": pos.tp,
                "live_pl": pos.profit, "margin": pos.margin,
                "open_time": datetime.fromtimestamp(pos.time).isoformat(), "status": "open",
            }, on_conflict="ticket").execute()
        except:
            pass
    
    try:
        db_trades = supabase.table("trades").select("ticket").eq("account_id", mt5_account_id).eq("status", "open").execute()
        if db_trades.data:
            for t in db_trades.data:
                if t["ticket"] not in current_tickets:
                    supabase.table("trades").update({"status": "closed"}).eq("ticket", t["ticket"]).execute()
    except:
        pass

def get_bot_status(mt5_account_id: str) -> bool:
    """Read bot_active from the bot_status table (separate from profiles to avoid trigger issues)."""
    try:
        result = supabase.table("bot_status").select("bot_active").eq("mt5_account_id", mt5_account_id).maybe_single().execute()
        if result.data:
            return result.data.get("bot_active", False)
        return False
    except Exception as e:
        print(f"[WARN] get_bot_status error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 70)
    print("  MOKABotTRADE — Generic Strategy Framework")
    print("  ALL trading logic is defined in Supabase JSONB")
    print("  No hardcoded indicators or conditions")
    print("=" * 70)
    
    if not mt5.initialize(login=LOGIN, password=PASSWORD, server=SERVER):
        print(f"[ERROR] MT5 connection failed: {mt5.last_error()}")
        sys.exit(1)
    
    account_info = mt5.account_info()
    if not account_info:
        print("[ERROR] Failed to get account info")
        mt5.shutdown()
        sys.exit(1)
    
    print(f"\n[OK] Connected to MT5")
    print(f"     Account: {account_info.login}")
    print(f"     Balance: ${account_info.balance:.2f}")
    print("=" * 70)
    
    MT5_ACCOUNT_ID = str(account_info.login)
    engine = StrategyEngine()
    
    print("\n[BRIDGE] Starting... (Ctrl+C to stop)")
    print("[INFO] Strategies are fetched from DB every 30 seconds")
    print("[INFO] Any DB change reflects immediately\n")
    
    cycle = 0
    while True:
        try:
            cycle += 1
            ts = datetime.now().strftime('%H:%M:%S')
            
            sync_account_balance(MT5_ACCOUNT_ID)
            sync_trades(MT5_ACCOUNT_ID)
            
            bot_active = get_bot_status(MT5_ACCOUNT_ID)
            
            print(f"--- Cycle {cycle} @ {ts} ---")
            print(f"[BALANCE] ${account_info.balance:.2f} | Equity: ${account_info.equity:.2f}")
            
            if bot_active:
                print(f"[BOT] ▶ RUNNING")
                engine.process_cycle(bot_active=True)
            else:
                print(f"[BOT] ⏸  STANDBY — Monitoring only")
            
            print(f"--- Next in 10s ---\n")
            time.sleep(10)
        
        except KeyboardInterrupt:
            print("\n[BRIDGE] Stopping...")
            mt5.shutdown()
            break
        
        except Exception as e:
            print(f"[FATAL] {e}")
            time.sleep(5)
