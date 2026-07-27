"""
MetaApi Cloud Client for MOKABot
=================================
Cloud-native MT5 connection via MetaApi.cloud
Eliminates need for local MT5 terminal.

Usage:
    client = MetaApiClient(token="your_api_token")
    await client.connect()
    balance, equity = await client.get_balance("account_id")
    positions = await client.get_positions("account_id")
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from metaapi_cloud_sdk import MetaApi


class MetaApiClient:
    """
    Cloud-native MT5 client using MetaApi.cloud
    Replaces local MT5 terminal connection.
    """
    
    def __init__(self, token: str):
        """
        Initialize MetaApi client.
        
        Args:
            token: MetaApi API token from https://app.metaapi.cloud/token
        """
        self.token = token
        self.api = MetaApi(token=token)
        self._connections: Dict[str, Any] = {}  # Cache connections per account
    
    async def connect(self, account_id: str) -> bool:
        """
        Connect to MetaApi account.
        
        Args:
            account_id: MetaApi account ID (not MT5 login)
        
        Returns:
            True if connected successfully
        """
        try:
            # Get the MT account from MetaApi
            account = await self.api.metatrader_account_api.get_account(account_id)
            
            # Get RPC connection
            connection = account.get_rpc_connection()
            await connection.connect()
            await connection.wait_synchronized()
            
            # Cache the connection
            self._connections[account_id] = {
                'account': account,
                'connection': connection
            }
            
            return True
            
        except Exception as e:
            print(f"[MetaApi] Connection failed for {account_id}: {e}")
            return False
    
    async def disconnect(self, account_id: str):
        """Disconnect from MetaApi account."""
        if account_id in self._connections:
            try:
                connection = self._connections[account_id]['connection']
                await connection.close()
            except:
                pass
            del self._connections[account_id]
    
    async def get_balance(self, account_id: str) -> Tuple[float, float]:
        """
        Get account balance and equity.
        
        Returns:
            (balance, equity) tuple
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return 0.0, 0.0
        
        try:
            connection = self._connections[account_id]['connection']
            info = await connection.get_account_information()
            return info.balance, info.equity
        except Exception as e:
            print(f"[MetaApi] Failed to get balance for {account_id}: {e}")
            return 0.0, 0.0
    
    async def get_positions(self, account_id: str) -> List[Dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return []
        
        try:
            connection = self._connections[account_id]['connection']
            positions = await connection.get_positions()
            
            # Convert to dictionary format compatible with existing code
            result = []
            for pos in positions:
                result.append({
                    'ticket': str(pos.ticket),
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'sl': pos.stop_loss,
                    'tp': pos.take_profit,
                    'profit': pos.current_profit or pos.profit,
                    'margin': pos.margin,
                    'time': pos.time,
                    'magic': pos.magic,
                    'comment': pos.comment
                })
            
            return result
            
        except Exception as e:
            print(f"[MetaApi] Failed to get positions for {account_id}: {e}")
            return []
    
    async def get_symbol_price(self, account_id: str, symbol: str) -> Optional[Dict]:
        """
        Get current symbol price (bid/ask).
        
        Returns:
            Dictionary with 'bid', 'ask', 'spread' keys
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return None
        
        try:
            connection = self._connections[account_id]['connection']
            price = await connection.get_symbol_price(symbol)
            
            return {
                'bid': price.bid,
                'ask': price.ask,
                'spread': price.ask - price.bid,
                'time': price.time
            }
        except Exception as e:
            print(f"[MetaApi] Failed to get symbol price for {symbol}: {e}")
            return None
    
    async def get_symbol_info(self, account_id: str, symbol: str) -> Optional[Dict]:
        """
        Get symbol specification.
        
        Returns:
            Dictionary with symbol info
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return None
        
        try:
            connection = self._connections[account_id]['connection']
            spec = await connection.get_symbol_specification(symbol)
            
            return {
                'name': spec.name,
                'point': spec.point,
                'digits': spec.digits,
                'spread': spec.spread,
                'trade_mode': spec.trade_mode,
                'volume_min': spec.min_volume,
                'volume_max': spec.max_volume,
                'volume_step': spec.volume_step,
                'swap_mode': spec.swap_mode,
                'swap_long': spec.swap_long,
                'swap_short': spec.swap_short
            }
        except Exception as e:
            print(f"[MetaApi] Failed to get symbol info for {symbol}: {e}")
            return None
    
    async def open_trade(
        self,
        account_id: str,
        symbol: str,
        order_type: str,  # 'BUY' or 'SELL'
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = ""
    ) -> Optional[str]:
        """
        Open a new trade.
        
        Args:
            account_id: MetaApi account ID
            symbol: Trading symbol
            order_type: 'BUY' or 'SELL'
            volume: Lot size
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment
        
        Returns:
            Order ticket if successful, None otherwise
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return None
        
        try:
            connection = self._connections[account_id]['connection']
            
            # Get current price
            price_data = await self.get_symbol_price(account_id, symbol)
            if not price_data:
                return None
            
            # Determine price and trade type
            if order_type.upper() == 'BUY':
                price = price_data['ask']
                trade_type = 'ORDER_TYPE_BUY'
            else:
                price = price_data['bid']
                trade_type = 'ORDER_TYPE_SELL'
            
            # Open trade
            result = await connection.create_market_order(
                symbol=symbol,
                trade_type=trade_type,
                volume=volume,
                stop_loss=sl,
                take_profit=tp,
                comment=comment
            )
            
            return str(result.order_ticket) if result else None
            
        except Exception as e:
            print(f"[MetaApi] Failed to open trade: {e}")
            return None
    
    async def close_position(self, account_id: str, ticket: str) -> bool:
        """
        Close a position by ticket.
        
        Returns:
            True if successful
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return False
        
        try:
            connection = self._connections[account_id]['connection']
            await connection.close_position(int(ticket))
            return True
        except Exception as e:
            print(f"[MetaApi] Failed to close position {ticket}: {e}")
            return False
    
    async def get_history(self, account_id: str, start_time: datetime = None) -> List[Dict]:
        """
        Get trade history.
        
        Returns:
            List of historical deals
        """
        if account_id not in self._connections:
            if not await self.connect(account_id):
                return []
        
        try:
            connection = self._connections[account_id]['connection']
            
            if start_time is None:
                start_time = datetime.now(timezone.utc) - timezone.timedelta(days=7)
            
            history = await connection.get_deals_history(start_time)
            
            result = []
            for deal in history:
                result.append({
                    'ticket': str(deal.ticket),
                    'symbol': deal.symbol,
                    'type': deal.type,
                    'volume': deal.volume,
                    'price': deal.price,
                    'profit': deal.profit,
                    'time': deal.time
                })
            
            return result
            
        except Exception as e:
            print(f"[MetaApi] Failed to get history for {account_id}: {e}")
            return []


# ============================================
# SYNC WRAPPER (for compatibility with existing code)
# ============================================

class SyncMetaApiClient:
    """
    Synchronous wrapper for MetaApiClient.
    Allows using MetaApi in non-async code.
    """
    
    def __init__(self, token: str):
        self.token = token
        self._client = MetaApiClient(token)
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop
    
    def connect(self, account_id: str) -> bool:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.connect(account_id))
    
    def disconnect(self, account_id: str):
        loop = self._get_loop()
        loop.run_until_complete(self._client.disconnect(account_id))
    
    def get_balance(self, account_id: str) -> Tuple[float, float]:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.get_balance(account_id))
    
    def get_positions(self, account_id: str) -> List[Dict]:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.get_positions(account_id))
    
    def get_symbol_price(self, account_id: str, symbol: str) -> Optional[Dict]:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.get_symbol_price(account_id, symbol))
    
    def get_symbol_info(self, account_id: str, symbol: str) -> Optional[Dict]:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.get_symbol_info(account_id, symbol))
    
    def open_trade(
        self,
        account_id: str,
        symbol: str,
        order_type: str,
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = ""
    ) -> Optional[str]:
        loop = self._get_loop()
        return loop.run_until_complete(
            self._client.open_trade(account_id, symbol, order_type, volume, sl, tp, comment)
        )
    
    def close_position(self, account_id: str, ticket: str) -> bool:
        loop = self._get_loop()
        return loop.run_until_complete(self._client.close_position(account_id, ticket))
