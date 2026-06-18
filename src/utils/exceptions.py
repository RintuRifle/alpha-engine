"""
Custom exception classes for the Quant Research Platform.

Provides granular error types for debugging — much better than generic
ValueError/RuntimeError. Each exception carries context about what went wrong.
"""


class QuantPlatformError(Exception):
    """Base exception for the platform. All custom exceptions inherit this."""

    def __init__(self, message: str, context: dict | None = None):
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.context:
            details = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} [{details}]"
        return base


class DataFetchError(QuantPlatformError):
    """Raised when data fetching from an external API fails."""

    def __init__(self, message: str, ticker: str = "", source: str = "yfinance"):
        super().__init__(message, context={"ticker": ticker, "source": source})


class InvalidStrategyError(QuantPlatformError):
    """Raised when an invalid strategy is specified or configured."""

    def __init__(self, message: str, strategy_name: str = ""):
        super().__init__(message, context={"strategy": strategy_name})


class InsufficientDataError(QuantPlatformError):
    """Raised when there is not enough data to compute signals or metrics."""

    def __init__(self, message: str, required: int = 0, available: int = 0):
        super().__init__(message, context={"required": required, "available": available})


class BacktestError(QuantPlatformError):
    """Raised when the backtesting engine encounters an unrecoverable error."""
    pass


class ConfigurationError(QuantPlatformError):
    """Raised when configuration is invalid or missing."""
    pass
