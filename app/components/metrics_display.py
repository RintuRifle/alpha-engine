import streamlit as st
import pandas as pd
from src.analytics.metrics import Metrics
from src.analytics.risk_manager import RiskManager

def render_metrics(equity_df: pd.DataFrame, trade_history: list):
    if equity_df.empty:
        return
        
    col1, col2, col3, col4 = st.columns(4)
    
    cagr = Metrics.cagr(equity_df)
    sharpe = Metrics.sharpe_ratio(equity_df)
    mdd = Metrics.max_drawdown(equity_df)
    total_trades = len(trade_history) // 2  # Approximate round trips
    
    col1.metric("CAGR", f"{cagr*100:.2f}%")
    col2.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col3.metric("Max Drawdown", f"{mdd*100:.2f}%")
    col4.metric("Total Trades", f"{total_trades}")
