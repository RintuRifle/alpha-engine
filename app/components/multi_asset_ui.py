"""
Multi-Asset Portfolio — backtest a strategy across multiple tickers simultaneously.

Runs the same strategy on each ticker independently, combines equity curves,
and provides portfolio-level metrics + correlation analysis.

This is how real portfolio managers test: not just "does it work on AAPL?"
but "does it work across a diversified portfolio?"
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data.cache_manager import CacheManager
from src.analytics.metrics import Metrics
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Pre-built portfolios
PRESET_PORTFOLIOS = {
    "Tech Giants": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
    "Diversified US": ["AAPL", "JPM", "JNJ", "XOM", "PG"],
    "FAANG": ["META", "AAPL", "AMZN", "NVDA", "GOOGL"],
    "ETF Mix": ["SPY", "QQQ", "IWM", "TLT", "GLD"],
}


def render_multi_asset(
    strategy_class,
    strategy_params: dict,
    backtest_engine_class,
    start_date: str,
    end_date: str,
    initial_capital: float = 10000.0,
    allocation: float = 0.95,
    allow_short: bool = False,
    use_stops: bool = False,
    atr_multiplier: float = 2.0,
) -> None:
    """
    Multi-asset backtest UI. Runs strategy across multiple tickers,
    shows individual + portfolio equity curves, and correlation matrix.
    """
    st.markdown("### <i class='fa-solid fa-globe' style='color: #45B7D1;'></i> Multi-Asset Portfolio", unsafe_allow_html=True)

    # Preset or custom tickers
    preset = st.selectbox("Portfolio Preset", ["Custom"] + list(PRESET_PORTFOLIOS.keys()))

    if preset == "Custom":
        tickers_input = st.text_input(
            "Tickers (comma-separated)",
            value="AAPL, MSFT, GOOGL, NVDA",
            help="Enter 2-10 tickers separated by commas",
        )
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    else:
        tickers = PRESET_PORTFOLIOS[preset]
        st.info(f"**{preset}:** {', '.join(tickers)}")

    if len(tickers) < 2:
        st.warning("Enter at least 2 tickers for multi-asset analysis.")
        return

    if len(tickers) > 10:
        st.warning("Maximum 10 tickers for performance reasons.")
        tickers = tickers[:10]

    capital_per_asset = initial_capital / len(tickers)

    if st.button("Run Multi-Asset Backtest", icon=":material/public:", type="primary"):
        _run_multi_asset(
            tickers, strategy_class, strategy_params, backtest_engine_class,
            start_date, end_date, capital_per_asset, allocation,
            allow_short, use_stops, atr_multiplier,
        )


def _run_multi_asset(
    tickers: list[str],
    strategy_class,
    strategy_params: dict,
    backtest_engine_class,
    start_date: str,
    end_date: str,
    capital_per_asset: float,
    allocation: float,
    allow_short: bool,
    use_stops: bool,
    atr_multiplier: float,
) -> None:
    """Execute multi-asset backtest and display results."""

    cache = CacheManager()
    progress = st.progress(0, text="Fetching data...")

    per_asset_results = {}
    per_asset_equity = {}
    per_asset_returns = {}
    errors = []

    for i, ticker in enumerate(tickers):
        pct = int((i / len(tickers)) * 100)
        progress.progress(pct, text=f"Processing {ticker}...")

        try:
            df = cache.get_data(ticker, start_date, end_date)
            strategy = strategy_class(**strategy_params)
            df_signals = strategy.generate_signals(df)

            engine = backtest_engine_class(
                data=df_signals,
                ticker=ticker,
                initial_capital=capital_per_asset,
                allocation=allocation,
                allow_short=allow_short,
                use_stops=use_stops,
                atr_multiplier=atr_multiplier,
            )
            portfolio = engine.run()
            equity_df = portfolio.get_equity_df()

            if not equity_df.empty:
                metrics = Metrics.compute_all(equity_df, portfolio.trade_history)
                per_asset_results[ticker] = metrics
                per_asset_equity[ticker] = equity_df["total_equity"]
                per_asset_returns[ticker] = equity_df["total_equity"].pct_change().dropna()
        except Exception as e:
            errors.append(f"{ticker}: {e}")
            logger.warning(f"Multi-asset failed for {ticker}: {e}")

    progress.progress(100, text="✅ Complete!")

    if errors:
        for err in errors:
            st.warning(f"⚠️ {err}")

    if not per_asset_results:
        st.error("No assets produced valid results.")
        return

    # ── Per-Asset Metrics Table ──
    st.markdown("### <i class='fa-solid fa-table-list' style='color: #FFD93D;'></i> Per-Asset Results", unsafe_allow_html=True)
    rows = []
    for ticker, m in per_asset_results.items():
        rows.append({
            "Ticker": ticker,
            "CAGR (%)": round(m["cagr"] * 100, 2),
            "Sharpe": round(m["sharpe_ratio"], 3),
            "Sortino": round(m["sortino_ratio"], 3),
            "Max DD (%)": round(m["max_drawdown"] * 100, 2),
            "Volatility (%)": round(m["volatility"] * 100, 2),
            "Win Rate (%)": round(m["win_rate"] * 100, 1),
            "Trades": m["total_trades"],
            "Omega": round(m["omega_ratio"], 2) if m["omega_ratio"] != float("inf") else 999,
        })

    df_results = pd.DataFrame(rows)
    st.dataframe(
        df_results.style.background_gradient(subset=["Sharpe"], cmap="RdYlGn")
        .background_gradient(subset=["CAGR (%)"], cmap="RdYlGn"),
        width='stretch',
    )

    # ── Portfolio Summary ──
    total_capital = capital_per_asset * len(per_asset_results)
    portfolio_equity = sum(per_asset_equity.values())

    if hasattr(portfolio_equity, 'iloc') and len(portfolio_equity) > 0:
        portfolio_return = (portfolio_equity.iloc[-1] / portfolio_equity.iloc[0] - 1) * 100
        avg_sharpe = np.mean([m["sharpe_ratio"] for m in per_asset_results.values()])
        avg_dd = np.mean([m["max_drawdown"] for m in per_asset_results.values()])

        st.markdown("### <i class='fa-solid fa-briefcase' style='color: #9B59B6;'></i> Portfolio Summary", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Portfolio Return", f"{portfolio_return:+.2f}%")
        c2.metric("Avg Sharpe", f"{avg_sharpe:.3f}")
        c3.metric("Avg Max DD", f"{avg_dd*100:.2f}%")
        c4.metric("Assets", f"{len(per_asset_results)}")

    # ── Overlaid Equity Curves ──
    st.markdown("### <i class='fa-solid fa-chart-line' style='color: #4ECDC4;'></i> Equity Curves", unsafe_allow_html=True)
    fig = go.Figure()
    colors = ["#00D4AA", "#FF6B6B", "#4ECDC4", "#FFD93D", "#45B7D1",
              "#FF8C00", "#9B59B6", "#E74C3C", "#2ECC71", "#3498DB"]

    for i, (ticker, equity) in enumerate(per_asset_equity.items()):
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity.values,
            mode="lines", name=ticker,
            line=dict(color=colors[i % len(colors)], width=2),
        ))

    fig.update_layout(
        xaxis_title="Date", yaxis_title="Value ($)",
        template="plotly_dark", height=450,
        margin=dict(l=20, r=20, t=10, b=20),
        hovermode="x unified",
    )
    st.plotly_chart(fig, width='stretch')

    # ── Correlation Matrix ──
    if len(per_asset_returns) >= 2:
        _render_correlation(per_asset_returns)


def _render_correlation(returns_dict: dict[str, pd.Series]) -> None:
    """Render inter-asset correlation heatmap."""
    st.markdown("### <i class='fa-solid fa-link' style='color: #E74C3C;'></i> Correlation Matrix", unsafe_allow_html=True)
    st.caption(
        "Low correlation between assets = better diversification. "
        "Target correlations below 0.5 for a robust portfolio."
    )

    # Build returns DataFrame
    returns_df = pd.DataFrame(returns_dict)
    # Align on common dates
    returns_df = returns_df.dropna()

    if returns_df.empty or len(returns_df) < 10:
        st.info("Not enough overlapping data for correlation analysis.")
        return

    corr = returns_df.corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdYlGn_r",  # Red = high corr (bad for diversification)
        zmin=-1, zmax=1,
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        hovertemplate="<b>%{x}</b> vs <b>%{y}</b>: %{z:.3f}<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark", height=400,
        margin=dict(l=20, r=20, t=10, b=20),
    )
    st.plotly_chart(fig, width='stretch')

    # Diversification score
    upper_tri = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    avg_corr = upper_tri.stack().mean()
    score = 1 - abs(avg_corr)

    col1, col2 = st.columns(2)
    col1.metric("Avg Correlation", f"{avg_corr:.3f}")
    if score > 0.7:
        col2.metric("Diversification Score", f"{score:.0%}", delta="Excellent ✅")
    elif score > 0.5:
        col2.metric("Diversification Score", f"{score:.0%}", delta="Good 🟡")
    else:
        col2.metric("Diversification Score", f"{score:.0%}", delta="Poor 🔴", delta_color="inverse")
