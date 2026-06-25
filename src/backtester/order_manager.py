"""
Order Manager — handles trade execution, position updates, and short selling.

Supports:
- Long positions: BUY to open, SELL to close
- Short positions (when allow_short=True): SELL to open short, BUY to cover

Short selling mechanics:
  When you short, you receive cash from selling borrowed shares.
  When you cover, you buy back shares to return them.
  Profit = (short_entry_price - cover_price) × quantity
"""

from .portfolio import Portfolio
from .transaction_costs import TransactionCosts
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OrderManager:
    def __init__(self, portfolio: Portfolio, transaction_costs: TransactionCosts,
                 allow_short: bool = False):
        self.portfolio = portfolio
        self.tc = transaction_costs
        self.allow_short = allow_short

    def execute_trade(self, date, ticker: str, action: str, quantity: float, raw_price: float):
        if quantity <= 0:
            return

        exec_price = self.tc.apply_costs(raw_price, action)
        current_qty = self.portfolio.positions.get(ticker, 0)

        if action == 'BUY':
            if current_qty < 0:
                # ── COVER SHORT: buying back shares to close short position ──
                cover_qty = min(quantity, abs(current_qty))
                notional = cover_qty * exec_price
                commission = self.tc.calculate_commission(notional)
                total_cost = notional + commission

                if total_cost > self.portfolio.cash:
                    cover_qty = int(self.portfolio.cash // (exec_price * (1 + self.tc.commission_pct)))
                    if cover_qty <= 0:
                        return
                    notional = cover_qty * exec_price
                    commission = self.tc.calculate_commission(notional)
                    total_cost = notional + commission

                self.portfolio.cash -= total_cost
                self.portfolio.positions[ticker] = current_qty + cover_qty
                if self.portfolio.positions[ticker] == 0:
                    del self.portfolio.positions[ticker]

                self.portfolio.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'COVER',
                    'quantity': cover_qty,
                    'price': exec_price,
                    'commission': commission,
                    'slippage': abs(exec_price - raw_price) * cover_qty
                })
                return

            # ── OPEN LONG: standard buy ──
            notional = quantity * exec_price
            commission = self.tc.calculate_commission(notional)
            total_cost = notional + commission

            if total_cost > self.portfolio.cash:
                logger.debug(f"Insufficient funds on {date} to buy {quantity} {ticker}. "
                             f"Need {total_cost}, have {self.portfolio.cash}")
                quantity = int(self.portfolio.cash // (exec_price * (1 + self.tc.commission_pct)))
                if quantity <= 0:
                    return
                notional = quantity * exec_price
                commission = self.tc.calculate_commission(notional)
                total_cost = notional + commission

            self.portfolio.cash -= total_cost
            self.portfolio.positions[ticker] = self.portfolio.positions.get(ticker, 0) + quantity

        elif action == 'SELL':
            if current_qty > 0:
                # ── CLOSE LONG: sell existing shares ──
                sell_qty = min(quantity, current_qty)
                if sell_qty <= 0:
                    return

                notional = sell_qty * exec_price
                commission = self.tc.calculate_commission(notional)
                net_proceeds = notional - commission

                self.portfolio.cash += net_proceeds
                self.portfolio.positions[ticker] -= sell_qty
                if self.portfolio.positions[ticker] == 0:
                    del self.portfolio.positions[ticker]

                quantity = sell_qty  # For trade log

            elif current_qty == 0 and self.allow_short:
                # ── OPEN SHORT: sell shares you don't own ──
                # Receive cash from the sale, but must post margin
                notional = quantity * exec_price
                commission = self.tc.calculate_commission(notional)
                net_proceeds = notional - commission

                # Require enough cash to cover potential loss (margin = 100% of notional)
                if notional > self.portfolio.cash:
                    quantity = int(self.portfolio.cash // (exec_price * (1 + self.tc.commission_pct)))
                    if quantity <= 0:
                        return
                    notional = quantity * exec_price
                    commission = self.tc.calculate_commission(notional)
                    net_proceeds = notional - commission

                self.portfolio.cash += net_proceeds
                self.portfolio.positions[ticker] = self.portfolio.positions.get(ticker, 0) - quantity

                self.portfolio.trade_history.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'SHORT',
                    'quantity': quantity,
                    'price': exec_price,
                    'commission': commission,
                    'slippage': abs(exec_price - raw_price) * quantity
                })
                return
            else:
                # No position and short selling not allowed
                return

        # Log trade (standard BUY or SELL)
        self.portfolio.trade_history.append({
            'date': date,
            'ticker': ticker,
            'action': action,
            'quantity': quantity,
            'price': exec_price,
            'commission': commission,
            'slippage': abs(exec_price - raw_price) * quantity
        })
