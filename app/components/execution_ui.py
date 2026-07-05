"""
Execution UI Component for Paper Trading.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

from src.execution.alpaca_broker import AlpacaBroker
from src.execution.gateway import ExecutionGateway

def render_execution_ui(inputs: Dict[str, Any]) -> None:
    """Render the live execution dashboard."""
    
    st.markdown("### <i class='fa-solid fa-satellite-dish' style='color: #9B59B6;'></i> Live Execution Gateway (Alpaca Paper Trading)", unsafe_allow_html=True)
    st.caption("Connect your strategy signals directly to Alpaca for live paper trading.")
    
    # ── API Credentials ──
    col1, col2 = st.columns(2)
    with col1:
        api_key = st.text_input("Alpaca API Key", type="password", key="alpaca_key")
    with col2:
        secret_key = st.text_input("Alpaca Secret Key", type="password", key="alpaca_secret")
        
    if not api_key or not secret_key:
        st.warning("Please enter your Alpaca Paper Trading API keys to connect.")
        return
        
    try:
        broker = AlpacaBroker(api_key, secret_key)
        gateway = ExecutionGateway(broker)
        
        # ── Account Summary ──
        st.markdown("#### Account Summary")
        account = broker.get_account_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", account["status"])
        c2.metric("Equity", f"${account['equity']:,.2f}")
        c3.metric("Buying Power", f"${account['buying_power']:,.2f}")
        c4.metric("Cash", f"${account['cash']:,.2f}")
        
        # ── Open Positions ──
        st.markdown("#### Open Positions")
        positions = broker.get_positions()
        if positions:
            df_pos = pd.DataFrame(positions)
            st.dataframe(df_pos.style.format({
                "market_value": "${:.2f}",
                "unrealized_pl": "${:.2f}",
                "unrealized_plpc": "{:.2%}"
            }), width='stretch')
        else:
            st.info("No open positions.")
            
        # ── Execute Daily Strategy ──
        st.markdown("#### Manual Execution")
        st.write(f"Execute {inputs['strategy']} for {inputs['ticker']}")
        if st.button("Generate Signals & Sync Portfolio", type="primary", icon=":material/sync:"):
            with st.spinner("Fetching latest data and running strategy..."):
                from src.data.cache_manager import CacheManager
                from app.streamlit_app import STRATEGY_MAP
                import datetime
                
                # Fetch recent data
                end_d = datetime.date.today()
                start_d = end_d - datetime.timedelta(days=365) # Need enough data for SMA200 etc
                
                cache = CacheManager()
                df = cache.get_data(inputs["ticker"], start_d.strftime("%Y-%m-%d"), end_d.strftime("%Y-%m-%d"))
                
                if df.empty:
                    st.error("Could not fetch data for ticker.")
                    return
                    
                strategy_class = STRATEGY_MAP.get(inputs["strategy"])
                strategy = strategy_class(**inputs.get("strategy_params", {}))
                
                df_signals = strategy.generate_signals(df)
                latest_signal = df_signals.iloc[-1]["signal"]
                current_price = df_signals.iloc[-1]["close"]
                
                st.write(f"**Latest Signal:** {'LONG (1)' if latest_signal == 1 else 'SHORT (-1)' if latest_signal == -1 else 'NEUTRAL (0)'}")
                st.write(f"**Current Price:** ${current_price:.2f}")
                
                gateway.sync_target_positions(inputs["ticker"], current_price, latest_signal, inputs.get("allocation", 0.95))
                st.success("Successfully synced portfolio with target signal!")
                st.rerun()
                
    except Exception as e:
        st.error(f"Execution Error: {e}")
