import pandas as pd
import numpy as np

class Metrics:
    @staticmethod
    def cagr(equity_df: pd.DataFrame) -> float:
        if equity_df.empty or len(equity_df) < 2: return 0.0
        start_val = equity_df['total_equity'].iloc[0]
        end_val = equity_df['total_equity'].iloc[-1]
        days = (equity_df.index[-1] - equity_df.index[0]).days
        if days == 0: return 0.0
        return (end_val / start_val) ** (365.0 / days) - 1

    @staticmethod
    def sharpe_ratio(equity_df: pd.DataFrame, risk_free_rate: float = 0.0) -> float:
        if equity_df.empty: return 0.0
        returns = equity_df['total_equity'].pct_change().dropna()
        if returns.std() == 0: return 0.0
        return (returns.mean() - risk_free_rate) / returns.std() * np.sqrt(252)

    @staticmethod
    def max_drawdown(equity_df: pd.DataFrame) -> float:
        if equity_df.empty: return 0.0
        cummax = equity_df['total_equity'].cummax()
        drawdown = (equity_df['total_equity'] - cummax) / cummax
        return drawdown.min()

    @staticmethod
    def win_rate(trade_history: list) -> float:
        if not trade_history: return 0.0
        # Simplistic: count winning round trips
        # Real system needs complex P&L per trade matching
        # Placeholder returns 50%
        return 0.50
