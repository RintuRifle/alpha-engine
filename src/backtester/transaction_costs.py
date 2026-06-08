class TransactionCosts:
    def __init__(self, commission_pct: float = 0.001, slippage_pct: float = 0.0005):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    def apply_costs(self, price: float, action: str) -> float:
        """
        Adjust execution price based on slippage.
        Returns the effective execution price.
        """
        if action == 'BUY':
            return price * (1 + self.slippage_pct)
        elif action == 'SELL':
            return price * (1 - self.slippage_pct)
        return price

    def calculate_commission(self, notional_value: float) -> float:
        """Calculate commission cost based on trade value."""
        return notional_value * self.commission_pct
