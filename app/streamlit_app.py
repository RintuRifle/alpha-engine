import streamlit as st
import pandas as pd
from src.data.cache_manager import CacheManager
from src.strategies.ma_crossover import MACrossover
from src.strategies.rsi_reversion import RSIReversion
from src.strategies.bollinger_bands import BollingerBands
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.buy_and_hold import BuyAndHold
from src.backtester.engine import BacktestEngine
from components import sidebar, charts, metrics_display
import yaml

st.set_page_config(page_title="Quant Research Platform", layout="wide")

def main():
    st.title("📈 Quant Research Platform")
    
    # Render sidebar and get inputs
    inputs = sidebar.render_sidebar()
    
    if st.sidebar.button("Run Backtest"):
        with st.spinner("Fetching data and running backtest..."):
            cache = CacheManager()
            try:
                # 1. Get Data
                df = cache.get_data(inputs['ticker'], inputs['start_date'], inputs['end_date'])
                
                # 2. Run Strategy
                strategy_map = {
                    'SMA Crossover': MACrossover(),
                    'RSI Reversion': RSIReversion(),
                    'Bollinger Bands': BollingerBands(),
                    'MACD': MACDStrategy(),
                    'Buy and Hold': BuyAndHold()
                }
                strategy = strategy_map[inputs['strategy']]
                df_with_signals = strategy.generate_signals(df)
                
                # 3. Run Backtest
                engine = BacktestEngine(
                    data=df_with_signals, 
                    ticker=inputs['ticker'], 
                    initial_capital=inputs['capital']
                )
                portfolio = engine.run()
                equity_df = portfolio.get_equity_df()
                
                # 4. Display Results
                st.subheader(f"Results for {inputs['ticker']} using {inputs['strategy']}")
                metrics_display.render_metrics(equity_df, portfolio.trade_history)
                charts.render_equity_curve(equity_df)
                
            except Exception as e:
                st.error(f"Error running backtest: {e}")

if __name__ == "__main__":
    main()
