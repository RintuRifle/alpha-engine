"""
Strategy registry for the API layer.

Maps strategy keys to classes and exposes JSON param schemas
so the frontend can render dynamic controls.
"""

from src.strategies.ma_crossover import MACrossover
from src.strategies.rsi_reversion import RSIReversion
from src.strategies.bollinger_bands import BollingerBands
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.buy_and_hold import BuyAndHold
from src.strategies.multi_factor import MultiFactorStrategy
from src.strategies.momentum_mr import MomentumMR
from src.strategies.vwap_strategy import VWAPStrategy
from src.strategies.custom_builder import CustomStrategy


def p(name, label, default, min_, max_, step, type_="int"):
    return {
        "name": name, "label": label, "type": type_,
        "default": default, "min": min_, "max": max_, "step": step,
    }


STRATEGIES = {
    "sma_crossover": {
        "label": "SMA Crossover",
        "class": MACrossover,
        "class_key": "MACrossover",  # key used by ParallelOptimizer
        "description": "Golden/death cross trend following",
        "params": [
            p("short_window", "Short Window", 50, 5, 100, 5),
            p("long_window", "Long Window", 200, 50, 300, 10),
        ],
    },
    "rsi_reversion": {
        "label": "RSI Reversion",
        "class": RSIReversion,
        "class_key": "RSIReversion",
        "description": "Buy oversold, sell overbought",
        "params": [
            p("window", "RSI Window", 14, 5, 30, 1),
            p("oversold", "Oversold Level", 30, 10, 45, 5),
            p("overbought", "Overbought Level", 70, 55, 90, 5),
        ],
    },
    "bollinger_bands": {
        "label": "Bollinger Bands",
        "class": BollingerBands,
        "class_key": "BollingerBands",
        "description": "Mean reversion at volatility bands",
        "params": [
            p("window", "Window", 20, 10, 50, 5),
            p("num_std", "Std Dev", 2.0, 1.0, 3.0, 0.25, "float"),
        ],
    },
    "macd": {
        "label": "MACD",
        "class": MACDStrategy,
        "class_key": "MACDStrategy",
        "description": "MACD line / signal line crossovers",
        "params": [
            p("fast_period", "Fast EMA", 12, 5, 20, 1),
            p("slow_period", "Slow EMA", 26, 15, 50, 1),
            p("signal_period", "Signal EMA", 9, 5, 15, 1),
        ],
    },
    "multi_factor": {
        "label": "Multi-Factor",
        "class": MultiFactorStrategy,
        "class_key": "MultiFactorStrategy",
        "description": "Score-based confluence of RSI/BB/MACD",
        "params": [
            p("min_score", "Min Score", 4, 1, 6, 1),
            p("rsi_window", "RSI Window", 14, 5, 30, 1),
            p("bb_window", "BB Window", 20, 10, 50, 5),
        ],
    },
    "momentum_mr": {
        "label": "Momentum + MR",
        "class": MomentumMR,
        "class_key": "MomentumMR",
        "description": "Momentum filter + mean-reversion entries",
        "params": [
            p("momentum_window", "Momentum Window", 252, 60, 300, 10),
            p("rsi_window", "RSI Window", 14, 5, 30, 1),
            p("entry_rsi", "Entry RSI", 40, 20, 50, 5),
            p("exit_rsi", "Exit RSI", 55, 50, 80, 5),
            p("trend_ma", "Trend MA", 200, 50, 300, 10),
        ],
    },
    "vwap_reversion": {
        "label": "VWAP Reversion",
        "class": VWAPStrategy,
        "class_key": "VWAPStrategy",
        "description": "Reversion to rolling VWAP",
        "params": [
            p("vwap_window", "VWAP Window", 20, 5, 60, 5),
            p("threshold", "Threshold", 0.02, 0.005, 0.10, 0.005, "float"),
        ],
    },
    "buy_and_hold": {
        "label": "Buy & Hold",
        "class": BuyAndHold,
        "class_key": "BuyAndHold",
        "description": "Passive benchmark strategy",
        "params": [],
    },
    "custom": {
        "label": "Custom Builder",
        "class": CustomStrategy,
        "class_key": "CustomStrategy",
        "description": "Build your own rules with indicators + pandas queries",
        "params": [],  # handled via custom payload
    },
}

# Display-name map (matches Streamlit STRATEGY_MAP labels, used by RegimeDetector compatibility)
LABEL_BY_KEY = {k: v["label"] for k, v in STRATEGIES.items()}


def get_strategy(key: str):
    if key not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{key}'. Valid: {list(STRATEGIES)}")
    return STRATEGIES[key]


def public_schema():
    """JSON-safe schema for the frontend."""
    out = []
    for key, s in STRATEGIES.items():
        out.append({
            "key": key,
            "label": s["label"],
            "description": s["description"],
            "params": s["params"],
        })
    return out
