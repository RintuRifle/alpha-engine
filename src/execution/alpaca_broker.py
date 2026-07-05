"""
Alpaca Paper Trading Broker Integration.
"""

import os
from typing import Dict, Any, List
import alpaca_trade_api as tradeapi

from src.utils.logger import get_logger

logger = get_logger(__name__)

class AlpacaBroker:
    """
    Interface to the Alpaca Trade API for paper trading.
    """
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://paper-api.alpaca.markets"):
        """Initialize the Alpaca API connection."""
        try:
            self.api = tradeapi.REST(
                key_id=api_key,
                secret_key=secret_key,
                base_url=base_url,
                api_version='v2'
            )
            self.account = self.api.get_account()
            logger.info(f"Connected to Alpaca. Status: {self.account.status}")
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            raise ConnectionError(f"Alpaca Connection Failed: {e}")
            
    def get_account_summary(self) -> Dict[str, Any]:
        """Get current account metrics."""
        self.account = self.api.get_account()
        return {
            "status": self.account.status,
            "cash": float(self.account.cash),
            "buying_power": float(self.account.buying_power),
            "equity": float(self.account.equity),
            "portfolio_value": float(self.account.portfolio_value)
        }
        
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        positions = self.api.list_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc)
            } for p in positions
        ]
        
    def close_all_positions(self):
        """Close all open positions (cancel all open orders)."""
        self.api.cancel_all_orders()
        self.api.close_all_positions()
        logger.info("Closed all Alpaca positions.")
        
    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market", time_in_force: str = "day") -> Any:
        """Place an order."""
        if qty <= 0:
            return None
            
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force
            )
            logger.info(f"Placed {side} order for {qty} {symbol}")
            return order
        except Exception as e:
            logger.error(f"Order failed for {symbol}: {e}")
            raise e
