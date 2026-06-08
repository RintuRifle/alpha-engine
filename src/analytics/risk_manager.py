import pandas as pd
import numpy as np

class RiskManager:
    @staticmethod
    def var_95(equity_df: pd.DataFrame) -> float:
        if equity_df.empty: return 0.0
        returns = equity_df['total_equity'].pct_change().dropna()
        return np.percentile(returns, 5)

    @staticmethod
    def cvar_95(equity_df: pd.DataFrame) -> float:
        if equity_df.empty: return 0.0
        returns = equity_df['total_equity'].pct_change().dropna()
        var = np.percentile(returns, 5)
        return returns[returns <= var].mean()

    @staticmethod
    def calculate_alpha_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series):
        if portfolio_returns.empty or benchmark_returns.empty: return 0.0, 1.0
        # Align series
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1, join='inner').dropna()
        if aligned.empty: return 0.0, 1.0
        cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
        var = np.var(aligned.iloc[:, 1])
        beta = cov / var if var != 0 else 1.0
        alpha = aligned.iloc[:, 0].mean() - beta * aligned.iloc[:, 1].mean()
        # Annualized
        return alpha * 252, beta
