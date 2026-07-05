"""
Custom Strategy Builder UI component.
"""

import streamlit as st
from typing import Dict, Any, List

def render_strategy_builder() -> Dict[str, Any]:
    """
    Render the custom strategy builder UI.
    
    Returns:
        Dict with "indicators", "buy_query", and "sell_query".
    """
    st.markdown("### <i class='fa-solid fa-hammer' style='color: #E67E22;'></i> Custom Strategy Builder", unsafe_allow_html=True)
    st.caption("Define your own strategy logic without writing code. Use the indicators defined below in your Buy/Sell logic.")

    # ── Indicators Definition ──
    st.markdown("#### 1. Define Indicators")
    
    if "custom_indicators" not in st.session_state:
        st.session_state.custom_indicators = [{"type": "SMA", "window": 50, "col_name": "SMA_50"}]
        
    for i, ind in enumerate(st.session_state.custom_indicators):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            itype = st.selectbox(f"Type ##{i}", ["SMA", "EMA", "RSI", "MACD"], index=["SMA", "EMA", "RSI", "MACD"].index(ind["type"]), key=f"ind_type_{i}")
            st.session_state.custom_indicators[i]["type"] = itype
        with col2:
            if itype in ["SMA", "EMA", "RSI"]:
                window = st.number_input(f"Window ##{i}", min_value=2, max_value=200, value=ind.get("window", 14), key=f"ind_win_{i}")
                st.session_state.custom_indicators[i]["window"] = window
                col_name_default = f"{itype}_{window}"
            elif itype == "MACD":
                st.session_state.custom_indicators[i]["fast"] = 12
                st.session_state.custom_indicators[i]["slow"] = 26
                st.session_state.custom_indicators[i]["signal"] = 9
                col_name_default = "MACD"
                st.caption("MACD uses default 12,26,9")
        with col3:
            col_name = st.text_input(f"Variable Name ##{i}", value=ind.get("col_name", col_name_default), key=f"ind_col_{i}")
            st.session_state.custom_indicators[i]["col_name"] = col_name
        with col4:
            st.write("")
            st.write("")
            if st.button("❌", key=f"del_ind_{i}"):
                st.session_state.custom_indicators.pop(i)
                st.rerun()

    if st.button("➕ Add Indicator"):
        st.session_state.custom_indicators.append({"type": "SMA", "window": 20, "col_name": "SMA_20"})
        st.rerun()

    st.markdown("---")
    
    # ── Logic Definition ──
    st.markdown("#### 2. Define Logic")
    st.caption("Use pandas eval syntax. Examples: `close > SMA_50 and RSI_14 < 30` or `MACD_line > MACD_signal`")
    
    if "buy_query" not in st.session_state:
        st.session_state.buy_query = "close > SMA_50"
    if "sell_query" not in st.session_state:
        st.session_state.sell_query = "close < SMA_50"
        
    buy_query = st.text_area("Buy Condition (Go Long)", value=st.session_state.buy_query, key="buy_query_input")
    st.session_state.buy_query = buy_query
    
    sell_query = st.text_area("Sell Condition (Go Short / Exit)", value=st.session_state.sell_query, key="sell_query_input")
    st.session_state.sell_query = sell_query

    return {
        "indicators": st.session_state.custom_indicators,
        "buy_query": buy_query,
        "sell_query": sell_query
    }
