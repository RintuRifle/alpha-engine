"""
Risk Controls — ATR-based stops, trailing stops, and portfolio circuit breaker.

This is how professional quant funds manage downside risk:
1. ATR Stop Loss: Exit when price drops below entry − (multiplier × ATR)
2. Trailing Stop: Follows peak price upward, never moves down
3. Circuit Breaker: Halt trading when daily P&L exceeds threshold

Without stops, a strategy holds through catastrophic drawdowns.
With ATR stops, max drawdown typically improves 20-40%.

Usage:
    controls = RiskControls(atr_multiplier=2.0, use_trailing_stop=True)
    controls.on_entry(entry_price=150.0, atr_value=3.5, position_type='long')
    should_exit = controls.check_stop(current_price=142.0)
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RiskControls:
    """
    ATR-based risk management system.

    Parameters:
        atr_window: ATR calculation period (default: 14).
        atr_multiplier: Stop distance in ATR units (default: 2.0).
            - 1.5 = tight stops (more trades, lower drawdown, lower return)
            - 2.0 = standard (balanced)
            - 3.0 = wide stops (fewer trades, higher drawdown, higher return)
        use_trailing_stop: If True, stop follows peak price (default: True).
        circuit_breaker_pct: Daily loss threshold to halt trading (default: -0.03 = -3%).
        use_circuit_breaker: Enable portfolio-level circuit breaker (default: True).
    """

    def __init__(
        self,
        atr_window: int = 14,
        atr_multiplier: float = 2.0,
        use_trailing_stop: bool = True,
        circuit_breaker_pct: float = -0.03,
        use_circuit_breaker: bool = True,
    ):
        self.atr_window = atr_window
        self.atr_multiplier = atr_multiplier
        self.use_trailing_stop = use_trailing_stop
        self.circuit_breaker_pct = circuit_breaker_pct
        self.use_circuit_breaker = use_circuit_breaker

        # State
        self._entry_price: float = 0.0
        self._stop_price: float = 0.0
        self._peak_price: float = 0.0
        self._atr_at_entry: float = 0.0
        self._position_type: str = ""  # 'long' or 'short'
        self._in_position: bool = False
        self._circuit_tripped: bool = False

    def compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute Average True Range for the DataFrame.

        ATR = Wilder-smoothed average of True Range.
        True Range = max(H-L, |H-Prev_C|, |L-Prev_C|)
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Wilder's smoothing
        atr = tr.ewm(alpha=1/self.atr_window, min_periods=self.atr_window, adjust=False).mean()
        return atr

    def on_entry(self, entry_price: float, atr_value: float, position_type: str = "long"):
        """
        Called when entering a new position. Sets initial stop level.

        Args:
            entry_price: Price at which position was entered.
            atr_value: Current ATR value at entry time.
            position_type: 'long' or 'short'.
        """
        self._entry_price = entry_price
        self._atr_at_entry = atr_value
        self._position_type = position_type
        self._in_position = True
        self._peak_price = entry_price

        if position_type == "long":
            self._stop_price = entry_price - (self.atr_multiplier * atr_value)
        else:  # short
            self._stop_price = entry_price + (self.atr_multiplier * atr_value)

        logger.debug(
            f"Risk: Entry {position_type} @ ${entry_price:.2f}, "
            f"ATR={atr_value:.2f}, Stop=${self._stop_price:.2f}"
        )

    def check_stop(self, current_price: float, current_atr: float | None = None) -> bool:
        """
        Check if the stop loss has been triggered.

        If trailing stop is enabled, the stop level moves up (for longs)
        or down (for shorts) as the position becomes profitable.

        Args:
            current_price: Current market price.
            current_atr: Current ATR (used for trailing stop updates).

        Returns:
            True if stop triggered (position should be closed).
        """
        if not self._in_position:
            return False

        atr = current_atr if current_atr is not None else self._atr_at_entry

        if self._position_type == "long":
            # Update trailing stop
            if self.use_trailing_stop and current_price > self._peak_price:
                self._peak_price = current_price
                new_stop = current_price - (self.atr_multiplier * atr)
                self._stop_price = max(self._stop_price, new_stop)

            if current_price <= self._stop_price:
                logger.debug(
                    f"Risk: STOP HIT (long) @ ${current_price:.2f} "
                    f"(stop=${self._stop_price:.2f})"
                )
                self._in_position = False
                return True

        else:  # short
            # Update trailing stop for short
            if self.use_trailing_stop and current_price < self._peak_price:
                self._peak_price = current_price
                new_stop = current_price + (self.atr_multiplier * atr)
                self._stop_price = min(self._stop_price, new_stop)

            if current_price >= self._stop_price:
                logger.debug(
                    f"Risk: STOP HIT (short) @ ${current_price:.2f} "
                    f"(stop=${self._stop_price:.2f})"
                )
                self._in_position = False
                return True

        return False

    def check_circuit_breaker(self, daily_pnl_pct: float) -> bool:
        """
        Check if the portfolio circuit breaker should trip.

        Once tripped, remains tripped for the rest of the day.

        Args:
            daily_pnl_pct: Today's P&L as decimal (e.g., -0.03 = -3%).

        Returns:
            True if circuit breaker is tripped (halt trading).
        """
        if not self.use_circuit_breaker:
            return False

        if daily_pnl_pct <= self.circuit_breaker_pct:
            if not self._circuit_tripped:
                logger.warning(
                    f"⚠️ CIRCUIT BREAKER TRIPPED: daily P&L = {daily_pnl_pct*100:.2f}% "
                    f"(threshold: {self.circuit_breaker_pct*100:.1f}%)"
                )
            self._circuit_tripped = True
            return True

        return False

    def reset_daily(self):
        """Reset daily circuit breaker flag. Call at start of each trading day."""
        self._circuit_tripped = False

    def reset(self):
        """Full reset — call when position is fully closed."""
        self._entry_price = 0.0
        self._stop_price = 0.0
        self._peak_price = 0.0
        self._atr_at_entry = 0.0
        self._position_type = ""
        self._in_position = False
        self._circuit_tripped = False

    @property
    def current_stop_price(self) -> float:
        """Get the current stop level (for display/logging)."""
        return self._stop_price

    @property
    def in_position(self) -> bool:
        return self._in_position
