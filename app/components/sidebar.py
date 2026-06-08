import streamlit as st
from datetime import date, timedelta

def render_sidebar():
    st.sidebar.header("Configuration")
    
    ticker = st.sidebar.text_input("Ticker", value="AAPL")
    
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", value=date.today() - timedelta(days=365*2))
    end_date = col2.date_input("End Date", value=date.today())
    
    capital = st.sidebar.number_input("Initial Capital", min_value=1000, value=10000, step=1000)
    
    strategy = st.sidebar.selectbox(
        "Strategy",
        ['SMA Crossover', 'RSI Reversion', 'Bollinger Bands', 'MACD', 'Buy and Hold']
    )
    
    return {
        'ticker': ticker,
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'capital': capital,
        'strategy': strategy
    }
