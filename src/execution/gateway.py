"""
Execution Gateway linking Alpha Engine to live brokers.
"""

from typing import Dict, Any, List
import pandas as pd

from src.execution.alpaca_broker import AlpacaBroker
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ExecutionGateway:
    """
    Translates strategy signals into live broker orders.
    """
    
    def __init__(self, broker: AlpacaBroker):
        self.broker = broker
        
    def sync_target_positions(self, ticker: str, current_price: float, signal: int, allocation_pct: float = 0.95):
        """
        Synchronize live portfolio with the target signal.
        
        Args:
            ticker: Asset ticker
            current_price: Current market price
            signal: 1 (Long), -1 (Short), 0 (Neutral)
            allocation_pct: Percent of total equity to deploy
        """
        account = self.broker.get_account_summary()
        target_value = account["equity"] * allocation_pct
        
        # Current position for ticker
        positions = self.broker.get_positions()
        current_qty = 0
        for p in positions:
            # Note: yfinance uses AAPL, Alpaca uses AAPL. Watch out for .NS (Indian stocks on US broker won't work)
            alpaca_ticker = ticker.split(".")[0] 
            if p["symbol"] == alpaca_ticker:
                current_qty = p["qty"]
                break
                
        # Determine target quantity
        target_qty = 0
        if signal == 1:
            target_qty = int(target_value / current_price)
        elif signal == -1:
            # We don't do shorting in this simple example unless enabled
            target_qty = -int(target_value / current_price)
            
        alpaca_ticker = ticker.split(".")[0]
            
        # Calculate delta
        delta_qty = target_qty - current_qty
        
        logger.info(f"Syncing {alpaca_ticker}: Current Qty={current_qty}, Target Qty={target_qty}, Delta={delta_qty}")
        
        if delta_qty > 0:
            self.broker.place_order(alpaca_ticker, delta_qty, "buy")
        elif delta_qty < 0:
            self.broker.place_order(alpaca_ticker, abs(delta_qty), "sell")
        else:
            logger.info(f"No action required for {alpaca_ticker}")
