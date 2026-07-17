"""
MOKABot Safety Engine
=====================
Modular safety middleware that runs sequential checks before any trade.
All parameters are fetched from Supabase tactics_settings table.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple, Any, List

import MetaTrader5 as mt5
from supabase import Client


class SafetyEngine:
    """
    Multi-layer safety checklist that runs before any trade signal.
    If any check returns False, the trade is aborted (Early Return).
    """

    def __init__(self, supabase: Client, user_id: str = None, account_id: str = None):
        self.supabase = supabase
        self.user_id = user_id
        self.account_id = account_id

        # Settings cache
        self._settings: Dict = {}
        self._last_fetch = 0
        self._fetch_interval = 10  # seconds

        # Daily trade counter
        self._daily_trade_count = 0
        self._daily_trade_date = datetime.now(timezone.utc).date()

        # Initial fetch
        self.refresh_settings()

    def log(self, level: str, message: str):
        prefix = f"[Safety:{self.account_id}]" if self.account_id else "[Safety]"
        print(f"{prefix} [{level}] {message}")

    def refresh_settings(self, force: bool = False):
        now = time.time()
        if not force and (now - self._last_fetch) < self._fetch_interval:
            return

        try:
            query = self.supabase.table('tactics_settings').select('*')

            if self.user_id:
                # Filter by user_id
                result = self.supabase.table('tactics_settings').select('*').execute()
                for row in (result.data or []):
                    key = row['key']
                    value = row['value']
                    # Only use rows matching user_id
                    if row.get('user_id') == self.user_id or row.get('user_id') is None:
                        self._settings[key] = value.get('value', value)
            else:
                result = query.execute()
                for row in (result.data or []):
                    self._settings[row['key']] = row['value'].get('value', row['value'])

            self._last_fetch = now
            self.log('DEBUG', f'Settings refreshed: {len(self._settings)} keys loaded')

        except Exception as e:
            self.log('ERROR', f'Failed to refresh settings: {e}')

    def get_setting(self, key: str, default: Any = None) -> Any:
        self.refresh_settings()
        return self._settings.get(key, default)

    def check_kill_switch(self) -> bool:
        if self.get_setting('kill_switch', False):
            self.log('WARN', 'KILL SWITCH ACTIVE - All trades blocked')
            return False
        return True

    def check_daily_drawdown(self, current_equity: float, start_equity: float) -> bool:
        limit_pct = self.get_setting('daily_drawdown_limit', 5.0)
        
        # If limit is None, disable the check
        if limit_pct is None:
            return True

        if start_equity <= 0:
            return True

        drawdown_pct = (start_equity - current_equity) / start_equity * 100

        if drawdown_pct >= limit_pct:
            self.log('WARN', f'Daily drawdown limit exceeded: {drawdown_pct:.2f}% >= {limit_pct}%')
            return False

        return True

    def check_spread(self, symbol: str) -> bool:
        max_spread = self.get_setting('max_spread', 30)

        tick = mt5.symbol_info_tick(symbol)

        if not tick:
            self.log('WARN', f'Could not get tick data for {symbol} - symbol may not be in Market Watch')
            return True

        info = mt5.symbol_info(symbol)

        if not info:
            self.log('WARN', f'Could not get symbol info for {symbol}')
            return True

        spread_points = int((tick.ask - tick.bid) / info.point)

        if spread_points > max_spread:
            self.log('WARN', f'Spread too high for {symbol}: {spread_points} > {max_spread}')
            return False

        return True

    def check_trading_hours(self) -> bool:
        start_hour = self.get_setting('trading_hours_start', 8)
        end_hour = self.get_setting('trading_hours_end', 22)

        current_hour = datetime.now(timezone.utc).hour

        if not (start_hour <= current_hour < end_hour):
            self.log('INFO', f'Outside trading hours: {current_hour} not in [{start_hour}, {end_hour})')
            return False

        return True

    def check_daily_trades(self) -> bool:
        max_trades = self.get_setting('max_daily_trades', 10)

        today = datetime.now(timezone.utc).date()

        if today != self._daily_trade_date:
            self._daily_trade_count = 0
            self._daily_trade_date = today

        if self._daily_trade_count >= max_trades:
            self.log('WARN', f'Daily trade limit reached: {self._daily_trade_count} >= {max_trades}')
            return False

        return True

    def check_volatility(self, symbol: str) -> bool:
        atr_multiplier = self.get_setting('atr_multiplier', 2.5)

        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)

        if not tick or not info:
            return True

        spread = tick.ask - tick.bid

        avg_spread = info.spread * info.point

        if avg_spread > 0 and spread > atr_multiplier * avg_spread:
            self.log('WARN', f'High volatility detected for {symbol}')
            return False

        return True

    def run_all_checks(
        self,
        symbol: str = None,
        current_equity: float = None,
        start_equity: float = None,
    ) -> Tuple[bool, str]:
        """Run all safety checks. Returns (passed, message)."""

        self.refresh_settings()

        checks = [
            ('Kill Switch', lambda: self.check_kill_switch()),
            ('Trading Hours', lambda: self.check_trading_hours()),
            ('Daily Trades', lambda: self.check_daily_trades()),
            ('Spread', lambda: self.check_spread(symbol)),
            ('Volatility', lambda: self.check_volatility(symbol)),
        ]

        # Only add drawdown check if equity values provided
        if current_equity is not None and start_equity is not None:
            checks.append(
                ('Daily Drawdown', lambda: self.check_daily_drawdown(current_equity, start_equity))
            )

        for name, check_fn in checks:
            try:
                if not check_fn():
                    return False, f'Failed: {name}'
            except Exception as e:
                self.log('ERROR', f"Check '{name}' raised exception: {e}")
                return False, f'Error in {name}: {e}'

        return (True, 'All checks passed')

    def record_trade(self):
        self._daily_trade_count += 1
        self.log('INFO', f'Trade recorded. Daily count: {self._daily_trade_count}')

    def calculate_lot_size(self, balance: float, sl_points: float, symbol: str) -> float:
        """Calculate position size based on risk parameters."""

        risk_pct = self.get_setting('risk_per_trade', 1.0) / 100
        risk_amount = balance * risk_pct

        info = mt5.symbol_info(symbol)

        if not info:
            self.log('ERROR', f'Could not get symbol info for {symbol}')
            return 0.01

        point_value = info.trade_tick_value / info.trade_tick_size

        if sl_points <= 0 or point_value <= 0:
            return info.volume_min

        lot_size = risk_amount / (sl_points * point_value)

        lot_size = max(info.volume_min, min(lot_size, info.volume_max))

        lot_step = info.volume_step

        lot_size = round(lot_size / lot_step) * lot_step

        self.log('INFO', f'Calculated lot size: {lot_size:.2f} (risk: ${risk_amount:.2f}, SL: {sl_points} pts)')

        return round(lot_size, 2)
