from .portfolio import Portfolio
from .transaction_costs import TransactionCosts
from src.utils.logger import get_logger

logger = get_logger(__name__)

class OrderManager:
    def __init__(self, portfolio: Portfolio, transaction_costs: TransactionCosts):
        self.portfolio = portfolio
        self.tc = transaction_costs

    def execute_trade(self, date, ticker: str, action: str, quantity: float, raw_price: float):
        if quantity <= 0:
            return

        exec_price = self.tc.apply_costs(raw_price, action)
        notional = quantity * exec_price
        commission = self.tc.calculate_commission(notional)
        total_cost = notional + commission

        if action == 'BUY':
            if total_cost > self.portfolio.cash:
                logger.debug(f"Insufficient funds on {date} to buy {quantity} {ticker}. Need {total_cost}, have {self.portfolio.cash}")
                # Adjust quantity down to what we can afford
                quantity = int(self.portfolio.cash // (exec_price * (1 + self.tc.commission_pct)))
                if quantity <= 0:
                    return
                notional = quantity * exec_price
                commission = self.tc.calculate_commission(notional)
                total_cost = notional + commission
                
            self.portfolio.cash -= total_cost
            self.portfolio.positions[ticker] = self.portfolio.positions.get(ticker, 0) + quantity
            
        elif action == 'SELL':
            current_qty = self.portfolio.positions.get(ticker, 0)
            if current_qty < quantity:
                quantity = current_qty # Cannot short sell in this simple model
                if quantity <= 0:
                    return
            
            notional = quantity * exec_price
            commission = self.tc.calculate_commission(notional)
            net_proceeds = notional - commission
            
            self.portfolio.cash += net_proceeds
            self.portfolio.positions[ticker] -= quantity
            if self.portfolio.positions[ticker] == 0:
                del self.portfolio.positions[ticker]

        # Log trade
        self.portfolio.trade_history.append({
            'date': date,
            'ticker': ticker,
            'action': action,
            'quantity': quantity,
            'price': exec_price,
            'commission': commission,
            'slippage': abs(exec_price - raw_price) * quantity
        })
