"""
Service layer: wraps /src modules into JSON-safe pipelines
consumed by the FastAPI routes. Mirrors the Streamlit wiring in
app/streamlit_app.py but returns pure data instead of rendering.
"""

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.data.cache_manager import CacheManager
from src.backtester.engine import BacktestEngine
from src.analytics.metrics import Metrics
from src.analytics.benchmark import Benchmark
from src.analytics.monte_carlo import MonteCarlo
from src.analytics.walk_forward import WalkForward
from src.analytics.parallel_optimizer import ParallelOptimizer
from src.strategies.regime_detector import RegimeDetector

from api.registry import STRATEGIES, get_strategy

TRADING_DAYS = 252


# ──────────────────────────── helpers ────────────────────────────

def _f(v) -> Optional[float]:
    """JSON-safe float (NaN/inf → None)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, 6)


def _dstr(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


def _series_points(s: pd.Series, key: str = "value") -> List[dict]:
    return [{"time": _dstr(t), key: _f(v)} for t, v in s.items()]


def _downsample(items: list, max_points: int = 400) -> list:
    if len(items) <= max_points:
        return items
    step = len(items) / max_points
    idx = [int(i * step) for i in range(max_points)]
    out = [items[i] for i in idx]
    if out[-1] is not items[-1]:
        out.append(items[-1])
    return out


def _fetch(ticker: str, start: str, end: str) -> pd.DataFrame:
    cache = CacheManager()
    df = cache.get_data(ticker, start, end)
    if df is None or df.empty:
        raise ValueError(f"No data returned for {ticker} ({start} → {end})")
    return df


def _build_strategy(strategy_key: str, params: dict, custom: Optional[dict]):
    spec = get_strategy(strategy_key)
    cls = spec["class"]
    if strategy_key == "custom":
        custom = custom or {}
        return spec, cls(
            indicators=custom.get("indicators", []),
            buy_query=custom.get("buy_query", ""),
            sell_query=custom.get("sell_query", ""),
        )
    # keep only known params
    valid = {p["name"] for p in spec["params"]}
    clean = {k: v for k, v in (params or {}).items() if k in valid}
    return spec, cls(**clean)


def _apply_regime_gate(strategy, df, regime_df, label):
    compat = RegimeDetector.get_regime_strategy_compatibility()
    compatible = [r for r, names in compat.items() if label in names]
    df_signals = strategy.generate_signals(df)
    if not compatible:
        return df_signals
    if "regime" in regime_df.columns and len(regime_df) == len(df_signals):
        mask = ~regime_df["regime"].isin(compatible)
        df_signals.loc[mask.values, "signal"] = 0
    return df_signals


def _equity_payload(equity_df: pd.DataFrame) -> List[dict]:
    eq = equity_df["total_equity"]
    peak = eq.cummax()
    dd = (eq / peak - 1.0)
    return [
        {"time": _dstr(t), "equity": _f(e), "drawdown": _f(d)}
        for t, e, d in zip(eq.index, eq.values, dd.values)
    ]


def _monthly_returns(equity_df: pd.DataFrame) -> dict:
    eq = equity_df["total_equity"]
    monthly = eq.resample("ME").last().pct_change()
    # first month vs series start
    if len(monthly) > 0:
        first_end = eq.resample("ME").last().index[0]
        monthly.iloc[0] = eq.loc[:first_end].iloc[-1] / eq.iloc[0] - 1.0
    years = sorted(set(monthly.index.year))
    grid = []
    for y in years:
        row = [None] * 12
        sel = monthly[monthly.index.year == y]
        for t, v in sel.items():
            row[t.month - 1] = _f(v)
        grid.append(row)
    yearly = eq.resample("YE").last().pct_change()
    if len(yearly) > 0:
        first_end = eq.resample("YE").last().index[0]
        yearly.iloc[0] = eq.loc[:first_end].iloc[-1] / eq.iloc[0] - 1.0
    ytotals = {t.year: _f(v) for t, v in yearly.items()}
    return {
        "years": [int(y) for y in years],
        "data": grid,
        "yearly": [ytotals.get(y) for y in years],
    }


def _rolling_metrics(equity_df: pd.DataFrame, window: int = 60) -> List[dict]:
    rets = equity_df["total_equity"].pct_change()
    mean = rets.rolling(window).mean()
    std = rets.rolling(window).std()
    downside = rets.where(rets < 0, 0.0).rolling(window).std()
    sharpe = (mean / std) * np.sqrt(TRADING_DAYS)
    sortino = (mean / downside) * np.sqrt(TRADING_DAYS)
    vol = std * np.sqrt(TRADING_DAYS)
    out = []
    for t in rets.index[window:]:
        out.append({
            "time": _dstr(t),
            "sharpe": _f(sharpe.loc[t]),
            "sortino": _f(sortino.loc[t]),
            "volatility": _f(vol.loc[t]),
        })
    return _downsample(out, 500)


def _returns_hist(equity_df: pd.DataFrame, bins: int = 40) -> dict:
    rets = equity_df["total_equity"].pct_change().dropna()
    if rets.empty:
        return {"bins": [], "counts": []}
    counts, edges = np.histogram(rets.values, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    return {
        "bins": [_f(c) for c in centers],
        "counts": [int(c) for c in counts],
        "mean": _f(rets.mean()),
        "std": _f(rets.std()),
        "skew": _f(rets.skew()),
        "kurtosis": _f(rets.kurtosis()),
    }


def _regime_segments(regime_df: pd.DataFrame) -> List[dict]:
    if regime_df is None or "regime" not in regime_df.columns or regime_df.empty:
        return []
    out = []
    prev = None
    for t, r in regime_df["regime"].items():
        if r != prev:
            out.append({"time": _dstr(t), "regime": str(r)})
            prev = r
    return out


# ──────────────────────────── pipelines ────────────────────────────

def run_backtest_job(progress, req: Dict[str, Any]) -> Dict[str, Any]:
    """Full single-strategy backtest pipeline."""
    ticker = req["ticker"].upper().strip()
    start, end = req["start_date"], req["end_date"]
    capital = float(req.get("capital", 100000))

    progress(5, f"Fetching data for {ticker}...")
    df = _fetch(ticker, start, end)

    progress(15, "Detecting market regime...")
    regime_df = RegimeDetector().detect(df)

    progress(25, f"Generating signals...")
    spec, strategy = _build_strategy(
        req["strategy"], req.get("params", {}), req.get("custom")
    )
    if req.get("regime_gate"):
        df_signals = _apply_regime_gate(strategy, df, regime_df, spec["label"])
    else:
        df_signals = strategy.generate_signals(df)

    progress(40, "Running backtest simulation...")
    engine = BacktestEngine(
        data=df_signals,
        ticker=ticker,
        initial_capital=capital,
        allocation=float(req.get("allocation", 0.95)),
        allow_short=bool(req.get("allow_short", False)),
        use_stops=bool(req.get("use_stops", False)),
        atr_multiplier=float(req.get("atr_multiplier", 2.0)),
        use_trailing_stop=bool(req.get("use_trailing_stop", True)),
        use_circuit_breaker=bool(req.get("use_circuit_breaker", False)),
        circuit_breaker_pct=float(req.get("circuit_breaker_pct", -0.03)),
    )
    portfolio = engine.run()
    equity_df = portfolio.get_equity_df()
    if equity_df.empty:
        raise ValueError("Backtest produced an empty equity curve.")

    progress(60, "Computing metrics...")
    metrics = Metrics.compute_all(equity_df, portfolio.trade_history)
    metrics = {k: _f(v) if isinstance(v, (int, float, np.floating)) else v
               for k, v in metrics.items()}
    metrics["final_equity"] = _f(equity_df["total_equity"].iloc[-1])
    metrics["initial_capital"] = _f(capital)

    progress(70, f"Fetching benchmark ({req.get('benchmark', 'SPY')})...")
    benchmark_payload = None
    bench_metrics = {}
    try:
        bench_ticker = req.get("benchmark", "SPY")
        bench_eq = Benchmark.get_benchmark_equity(
            bench_ticker, start, end, initial_value=capital
        )
        if bench_eq is not None and len(bench_eq) > 0:
            bseries = bench_eq if isinstance(bench_eq, pd.Series) else bench_eq.iloc[:, 0]
            benchmark_payload = [
                {"time": _dstr(t), "equity": _f(v)} for t, v in bseries.items()
            ]
            bench_metrics["benchmark_return"] = _f(bseries.iloc[-1] / bseries.iloc[0] - 1)
    except Exception:
        benchmark_payload = None

    progress(85, "Running Monte Carlo simulation...")
    port_returns = equity_df["total_equity"].pct_change().dropna()
    mc_payload = None
    try:
        stress_prob = 0.10 if req.get("stress_test") else 0.0
        sim_df = MonteCarlo.simulate_paths(
            port_returns, num_sims=int(req.get("mc_sims", 500)),
            stress_probability=stress_prob,
        )
        if not sim_df.empty:
            qs = sim_df.quantile([0.05, 0.25, 0.50, 0.75, 0.95], axis=1).T
            mc_payload = {
                "p05": [_f(v) for v in qs[0.05]],
                "p25": [_f(v) for v in qs[0.25]],
                "p50": [_f(v) for v in qs[0.50]],
                "p75": [_f(v) for v in qs[0.75]],
                "p95": [_f(v) for v in qs[0.95]],
                "stats": {k: _f(v) for k, v in MonteCarlo.summary_stats(sim_df).items()},
            }
            if req.get("stress_test"):
                mc_payload["stress"] = [
                    {k: (_f(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in row.items()}
                    for row in MonteCarlo.stress_test_summary(port_returns)
                ]
    except Exception:
        mc_payload = None

    progress(95, "Packaging results...")
    candles = [
        {
            "time": _dstr(t),
            "open": _f(r["open"]), "high": _f(r["high"]),
            "low": _f(r["low"]), "close": _f(r["close"]),
            "volume": _f(r.get("volume", 0)),
        }
        for t, r in df.iterrows()
    ]
    trades = [
        {
            "time": _dstr(t["date"]),
            "action": str(t["action"]),
            "quantity": _f(t["quantity"]),
            "price": _f(t["price"]),
            "commission": _f(t["commission"]),
            "slippage": _f(t["slippage"]),
        }
        for t in portfolio.trade_history
    ]

    warning = None
    if len(trades) == 0:
        warning = (
            f"0 trades executed. {ticker} opened at "
            f"${_f(df['close'].iloc[0])} — either price exceeds available capital "
            f"or the strategy generated no signals in this window."
        )

    return {
        "ticker": ticker,
        "strategy_key": req["strategy"],
        "strategy_label": spec["label"],
        "strategy_name": strategy.name,
        "params": req.get("params", {}),
        "start_date": start,
        "end_date": end,
        "metrics": {**metrics, **bench_metrics},
        "candles": candles,
        "trades": trades,
        "equity": _equity_payload(equity_df),
        "benchmark": benchmark_payload,
        "monthly_returns": _monthly_returns(equity_df),
        "rolling": _rolling_metrics(equity_df),
        "returns_hist": _returns_hist(equity_df),
        "monte_carlo": mc_payload,
        "regimes": _regime_segments(regime_df),
        "warning": warning,
    }


def run_compare_job(progress, req: Dict[str, Any]) -> Dict[str, Any]:
    """Run all standard strategies with default params, side by side."""
    ticker = req["ticker"].upper().strip()
    start, end = req["start_date"], req["end_date"]
    capital = float(req.get("capital", 100000))

    progress(5, f"Fetching data for {ticker}...")
    df = _fetch(ticker, start, end)

    keys = [k for k in STRATEGIES if k != "custom"]
    results = []
    for i, key in enumerate(keys):
        spec = STRATEGIES[key]
        progress(10 + int(85 * i / len(keys)), f"Backtesting {spec['label']}...")
        try:
            strategy = spec["class"]()
            df_signals = strategy.generate_signals(df)
            engine = BacktestEngine(
                data=df_signals, ticker=ticker, initial_capital=capital,
                allocation=float(req.get("allocation", 0.95)),
            )
            portfolio = engine.run()
            equity_df = portfolio.get_equity_df()
            if equity_df.empty:
                continue
            metrics = Metrics.compute_all(equity_df, portfolio.trade_history)
            results.append({
                "key": key,
                "label": spec["label"],
                "metrics": {k: _f(v) for k, v in metrics.items()},
                "final_equity": _f(equity_df["total_equity"].iloc[-1]),
                "equity": _downsample(_equity_payload(equity_df), 300),
            })
        except Exception as e:
            results.append({"key": key, "label": spec["label"], "error": str(e)})

    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: (r["metrics"].get("sharpe_ratio") or -999), reverse=True)
    errs = [r for r in results if "error" in r]
    return {"ticker": ticker, "capital": _f(capital), "results": ok + errs}


def run_optimize_job(progress, req: Dict[str, Any]) -> Dict[str, Any]:
    """Grid-search optimization with heatmap output."""
    ticker = req["ticker"].upper().strip()
    spec = get_strategy(req["strategy"])
    param_grid = req["param_grid"]  # {param: [values]}
    if not param_grid:
        raise ValueError("param_grid is required")

    progress(5, f"Fetching data for {ticker}...")
    df = _fetch(ticker, req["start_date"], req["end_date"])

    total = 1
    for v in param_grid.values():
        total *= max(1, len(v))
    if total > 2000:
        raise ValueError(f"Grid too large ({total} combos). Max 2000.")

    progress(15, f"Optimizing {total} combinations...")
    out = ParallelOptimizer.grid_search(
        strategy_name=spec["class_key"],
        param_grid=param_grid,
        data=df,
        ticker=ticker,
        initial_capital=float(req.get("capital", 100000)),
        metric=req.get("metric", "sharpe_ratio"),
        n_jobs=int(req.get("n_jobs", -1)),
    )

    progress(95, "Packaging results...")
    clean_results = []
    for r in out["all_results"][:50]:
        if "error" in r:
            continue
        clean_results.append({
            "params": r["params"],
            "value": _f(r.get(out["metric_name"], 0.0)),
            "cagr": _f(r.get("cagr", 0.0)),
            "max_drawdown": _f(r.get("max_drawdown", 0.0)),
        })
    hm = out.get("heatmap_data")
    if hm:
        hm = {
            "x_param": hm["x_param"], "y_param": hm["y_param"],
            "x_values": hm["x_values"], "y_values": hm["y_values"],
            "z_values": [[_f(v) for v in row] for row in hm["z_values"]],
        }
    return {
        "ticker": ticker,
        "strategy_label": spec["label"],
        "metric": out["metric_name"],
        "best_params": out["best_params"],
        "best_value": _f(out["best_metric_value"]),
        "total_combinations": out["total_combinations"],
        "elapsed_seconds": out.get("elapsed_seconds"),
        "top_results": clean_results,
        "heatmap": hm,
    }


def run_walkforward_job(progress, req: Dict[str, Any]) -> Dict[str, Any]:
    """Rolling-window out-of-sample analysis."""
    ticker = req["ticker"].upper().strip()
    spec, _ = get_strategy(req["strategy"]), None

    progress(5, f"Fetching data for {ticker}...")
    df = _fetch(ticker, req["start_date"], req["end_date"])

    progress(20, "Running walk-forward windows...")
    results = WalkForward.run_walk_forward(
        df=df,
        strategy_class=spec["class"],
        strategy_params=req.get("params", {}),
        backtest_engine_class=BacktestEngine,
        ticker=ticker,
        n_splits=int(req.get("n_splits", 5)),
        train_ratio=float(req.get("train_ratio", 0.7)),
        initial_capital=float(req.get("capital", 100000)),
    )
    clean = []
    for r in results:
        clean.append({
            "window": r["window"],
            "train_size": r["train_size"],
            "test_size": r["test_size"],
            "test_return": _f(r["test_return"]),
            "num_trades": r["num_trades"],
            "error": r.get("error"),
        })
    returns = [r["test_return"] for r in clean if r["test_return"] is not None]
    positive = sum(1 for r in returns if r > 0)
    return {
        "ticker": ticker,
        "strategy_label": spec["label"],
        "windows": clean,
        "summary": {
            "avg_return": _f(np.mean(returns)) if returns else None,
            "consistency": _f(positive / len(returns)) if returns else None,
            "n_windows": len(clean),
        },
    }


def get_ohlcv(ticker: str, start: str, end: str) -> Dict[str, Any]:
    df = _fetch(ticker.upper().strip(), start, end)
    return {
        "ticker": ticker.upper().strip(),
        "candles": [
            {
                "time": _dstr(t),
                "open": _f(r["open"]), "high": _f(r["high"]),
                "low": _f(r["low"]), "close": _f(r["close"]),
                "volume": _f(r.get("volume", 0)),
            }
            for t, r in df.iterrows()
        ],
    }
