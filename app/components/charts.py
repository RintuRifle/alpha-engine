import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_equity_curve(equity_df: pd.DataFrame):
    if equity_df.empty:
        st.warning("No equity data to display.")
        return
        
    st.markdown("### Equity Curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_df.index, y=equity_df['total_equity'], mode='lines', name='Equity'))
    
    fig.update_layout(
        title="Portfolio Total Equity Over Time",
        xaxis_title="Date",
        yaxis_title="Total Equity ($)",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
