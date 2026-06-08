class PositionSizer:
    def __init__(self, method: str = 'fixed_capital', **params):
        self.method = method
        self.params = params

    def get_quantity(self, price: float, available_capital: float) -> float:
        """Returns the number of shares to buy."""
        if self.method == 'fixed_capital':
            allocation = self.params.get('allocation', 1.0)
            target_capital = available_capital * allocation
            # Integer shares only
            return int(target_capital // price)
        elif self.method == 'fixed_shares':
            return self.params.get('shares', 100)
        else:
            raise ValueError(f"Unknown sizing method: {self.method}")
