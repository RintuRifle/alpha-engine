"""
Position sizing module for the backtester.

Determines HOW MUCH capital to allocate per trade. Supports multiple methods:
- fixed_capital: Allocate a fixed percentage of available capital per trade.
- fixed_shares: Buy a fixed number of shares per trade.
- kelly: Kelly Criterion — mathematically optimal sizing based on win rate and payoff.

IMPORTANT: If the computed quantity is 0 (e.g., stock price > allocation budget),
the sizer falls back to buying 1 share — as long as the full share price is
affordable. This prevents the silent "0 trades forever" bug when capital is small.
"""

from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PositionSizer:
    """
    Calculates the number of shares to buy for each trade based on the
    configured sizing method.
    """

    def __init__(self, method: str = "fixed_capital", **params):
        """
        Args:
            method: Sizing method — 'fixed_capital', 'fixed_shares', or 'kelly'.
            **params: Method-specific parameters:
                - allocation (float): For fixed_capital, fraction of capital (e.g., 0.10 = 10%).
                - shares (int): For fixed_shares, number of shares to buy.
                - win_rate (float): For kelly, historical win rate (0.0-1.0).
                - avg_win (float): For kelly, average winning trade return.
                - avg_loss (float): For kelly, average losing trade return (positive number).
        """
        self.method = method
        self.params = params

    def get_quantity(self, price: float, available_capital: float) -> int:
        """
        Calculate the number of shares to trade.

        Args:
            price: Current market price per share.
            available_capital: Cash available for trading.

        Returns:
            Integer number of shares (always whole shares, rounded down).
            Returns 0 if the stock is completely unaffordable.
        """
        if price <= 0 or available_capital <= 0:
            return 0

        if self.method == "fixed_capital":
            qty = self._fixed_capital_pct(price, available_capital)
        elif self.method == "fixed_shares":
            qty = self._fixed_shares(price, available_capital)
        elif self.method == "kelly":
            qty = self._kelly_criterion(price, available_capital)
        else:
            logger.warning(f"Unknown sizing method '{self.method}', falling back to fixed_capital")
            qty = self._fixed_capital_pct(price, available_capital)

        # ── Minimum 1-share fallback ──────────────────────────────────────
        # If the allocation budget can't afford even 1 share, but the full
        # capital CAN afford it, buy exactly 1 share. This prevents the
        # silent "0 trades forever" bug when capital < 10x stock price.
        if qty == 0 and price <= available_capital:
            logger.debug(
                f"Allocation gave 0 shares @ ${price:.2f} "
                f"(budget=${available_capital * self.params.get('allocation', 0.1):.2f}). "
                f"Falling back to 1 share."
            )
            return 1

        return qty

    def _fixed_capital_pct(self, price: float, available_capital: float) -> int:
        """
        Allocate a fixed percentage of available capital.

        Example: With $10,000 capital and 10% allocation, use $1,000 per trade.
        """
        allocation = self.params.get("allocation", 0.10)
        target_capital = available_capital * allocation
        qty = int(target_capital // price)
        logger.debug(
            f"FixedCapital: {allocation*100:.0f}% of ${available_capital:.0f}"
            f" = {qty} shares @ ${price:.2f}"
        )
        return qty

    def _fixed_shares(self, price: float, available_capital: float) -> int:
        """Buy a fixed number of shares, if affordable."""
        shares = self.params.get("shares", 100)
        total_cost = shares * price
        if total_cost > available_capital:
            # Can't afford full position — buy what we can
            shares = int(available_capital // price)
        return shares

    def _kelly_criterion(self, price: float, available_capital: float) -> int:
        """
        Kelly Criterion — mathematically optimal bet sizing.

        Formula: f* = (W / A) - ((1 - W) / B)
        Where:
            W = win probability
            A = average loss amount
            B = average win amount
            f* = fraction of capital to risk

        The result is clamped to [0, 0.25] to prevent over-leveraging.
        """
        win_rate = self.params.get("win_rate", 0.5)
        avg_win = self.params.get("avg_win", 0.02)    # 2% average win
        avg_loss = self.params.get("avg_loss", 0.02)  # 2% average loss

        if avg_loss == 0 or avg_win == 0:
            logger.warning("Kelly: avg_win or avg_loss is 0, falling back to 5%")
            kelly_fraction = 0.05
        else:
            kelly_fraction = (win_rate / avg_loss) - ((1 - win_rate) / avg_win)

        # Clamp to prevent over-betting (half-Kelly is safer in practice)
        kelly_fraction = max(0.0, min(kelly_fraction * 0.5, 0.25))

        target_capital = available_capital * kelly_fraction
        qty = int(target_capital // price)

        logger.debug(
            f"Kelly: f*={kelly_fraction*100:.1f}%, target=${target_capital:.0f}, "
            f"qty={qty} @ ${price:.2f}"
        )
        return qty
