import pandas as pd
from typing import Dict, List, Any
from src.utils.type_hints import TradeRecord

class Portfolio:
    """Virtual Wallet tracking cash, positions, and equity curve."""
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, float] = {}
        self.trade_history: List[TradeRecord] = []
        self.equity_curve: List[Dict[str, Any]] = []

    def update_equity(self, date: Any, current_prices: Dict[str, float]):
        """Records total value of cash + open positions on a given date."""
        positions_value = sum(qty * current_prices.get(ticker, 0.0) 
                              for ticker, qty in self.positions.items())
        total_equity = self.cash + positions_value
        self.equity_curve.append({
            'date': date,
            'cash': self.cash,
            'positions_value': positions_value,
            'total_equity': total_equity
        })

    def get_equity_df(self) -> pd.DataFrame:
        if not self.equity_curve:
            return pd.DataFrame()
        df = pd.DataFrame(self.equity_curve)
        df.set_index('date', inplace=True)
        return df
