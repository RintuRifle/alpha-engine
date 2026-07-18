"""
Execution realism model — bid-ask spread, slippage models, liquidity caps.

Replaces the flat TransactionCosts assumption with configurable market
microstructure effects:

  Reference price (bar open)
    → ± half-spread            (BUY lifts the ask, SELL hits the bid)
    → + slippage               (fixed bps | volatility-scaled | volume impact)
    → participation cap        (can't be >X% of the bar's volume → partial fill)

All assumptions are explicit and surfaced to the API result so backtests are
honest about what they model — and what they don't.
"""

import math
from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

SLIPPAGE_MODELS = ("fixed", "volatility", "volume")


class ExecutionModel:
    """
    Drop-in replacement for TransactionCosts with microstructure realism.

    Args:
        commission_pct: Commission as fraction of notional (0.001 = 10 bps).
        spread_bps: Full bid-ask spread in basis points. BUY pays +spread/2,
            SELL receives -spread/2 off the reference price.
        slippage_model:
            'fixed'      → constant slippage_bps.
            'volatility' → vol_coef × (bar high-low range as % of open).
                           Wide bars = chaotic tape = worse fills.
            'volume'     → square-root market impact:
                           impact_bps × sqrt(quantity / bar_volume).
                           Bigger orders relative to liquidity = worse fills.
        slippage_bps: Slippage for the 'fixed' model (basis points).
        vol_coef: Fraction of the bar range paid as slippage ('volatility').
        impact_bps: Impact at 100% participation ('volume' model).
        max_participation: Max fraction of a bar's volume one order may take
            (1.0 = unlimited). Excess quantity is cut → partial fill.
        short_margin_pct: Cash collateral required to open a short, as a
            fraction of notional (1.0 = 100%, fully covered).
    """

    def __init__(
        self,
        commission_pct: float = 0.001,
        spread_bps: float = 0.0,
        slippage_model: str = "fixed",
        slippage_bps: float = 5.0,
        vol_coef: float = 0.1,
        impact_bps: float = 10.0,
        max_participation: float = 1.0,
        short_margin_pct: float = 1.0,
    ):
        if slippage_model not in SLIPPAGE_MODELS:
            raise ValueError(
                f"slippage_model must be one of {SLIPPAGE_MODELS}, got '{slippage_model}'"
            )
        self.commission_pct = commission_pct
        self.spread_bps = max(0.0, spread_bps)
        self.slippage_model = slippage_model
        self.slippage_bps = max(0.0, slippage_bps)
        self.vol_coef = max(0.0, vol_coef)
        self.impact_bps = max(0.0, impact_bps)
        self.max_participation = min(1.0, max(0.001, max_participation))
        self.short_margin_pct = max(0.0, short_margin_pct)

    # ── pricing ──────────────────────────────────────────────────────

    def _slippage_pct(self, bar: Optional[dict], quantity: float) -> float:
        if self.slippage_model == "fixed" or bar is None:
            return self.slippage_bps / 1e4

        if self.slippage_model == "volatility":
            try:
                o = float(bar["open"])
                rng = float(bar["high"]) - float(bar["low"])
                if o > 0 and rng >= 0:
                    return self.vol_coef * (rng / o)
            except (KeyError, TypeError, ValueError):
                pass
            return self.slippage_bps / 1e4

        # volume (square-root impact)
        try:
            vol = float(bar.get("volume") or 0)
            if vol > 0 and quantity > 0:
                participation = min(1.0, quantity / vol)
                return (self.impact_bps / 1e4) * math.sqrt(participation)
        except (TypeError, ValueError):
            pass
        return self.slippage_bps / 1e4

    def effective_price(
        self,
        raw_price: float,
        action: str,
        bar: Optional[dict] = None,
        quantity: float = 0.0,
    ) -> float:
        """Reference price adjusted for half-spread + slippage, by side."""
        half_spread = self.spread_bps / 2.0 / 1e4
        slip = self._slippage_pct(bar, quantity)
        adverse = half_spread + slip
        if action in ("BUY",):  # paying up (also used for COVER)
            return raw_price * (1 + adverse)
        if action in ("SELL",):  # hitting the bid (also used for SHORT)
            return raw_price * (1 - adverse)
        return raw_price

    # ── liquidity ────────────────────────────────────────────────────

    def cap_quantity(self, quantity: float, bar: Optional[dict]) -> tuple[int, bool]:
        """Cap order size at max_participation × bar volume. → (qty, was_capped)"""
        if bar is None or self.max_participation >= 1.0:
            return int(quantity), False
        try:
            vol = float(bar.get("volume") or 0)
        except (TypeError, ValueError):
            return int(quantity), False
        if vol <= 0:
            return int(quantity), False
        allowed = int(vol * self.max_participation)
        if quantity > allowed:
            logger.debug(
                f"Liquidity cap: requested {quantity}, allowed {allowed} "
                f"({self.max_participation:.0%} of {vol:.0f} bar volume)"
            )
            return max(0, allowed), True
        return int(quantity), False

    # ── TransactionCosts-compatible interface ────────────────────────

    def apply_costs(self, price: float, action: str) -> float:
        return self.effective_price(price, action)

    def calculate_commission(self, notional_value: float) -> float:
        return notional_value * self.commission_pct

    # ── transparency ─────────────────────────────────────────────────

    def assumptions(self) -> Dict[str, Any]:
        return {
            "account": "cash (no leverage)",
            "commission_pct": self.commission_pct,
            "spread_bps": self.spread_bps,
            "slippage_model": self.slippage_model,
            "slippage_bps": self.slippage_bps if self.slippage_model == "fixed" else None,
            "vol_coef": self.vol_coef if self.slippage_model == "volatility" else None,
            "impact_bps": self.impact_bps if self.slippage_model == "volume" else None,
            "max_participation": self.max_participation,
            "short_margin_pct": self.short_margin_pct,
            "fills": "entries capped by participation; exits always fill (conservative on entry, avoids stuck positions)",
        }
