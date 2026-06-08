class QuantPlatformError(Exception):
    """Base exception for the platform."""
    pass

class DataFetchError(QuantPlatformError):
    """Raised when data fetching from API fails."""
    pass

class InvalidStrategyError(QuantPlatformError):
    """Raised when an invalid strategy is specified or configured."""
    pass

class InsufficientDataError(QuantPlatformError):
    """Raised when there is not enough data to compute signals or metrics."""
    pass
