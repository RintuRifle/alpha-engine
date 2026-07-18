"""
Exchange trading-session registry.

Maps tickers to their exchange session (open/close times, timezone) so the
resampler and engine can be session-aware instead of assuming midnight
boundaries or a fixed 6.5h day.

Suffix-based detection keeps it dependency-free; swap in `exchange_calendars`
later for full holiday support.
"""

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Session:
    name: str
    tz: str
    open_time: time
    close_time: time

    @property
    def hours(self) -> float:
        o = self.open_time.hour * 3600 + self.open_time.minute * 60
        c = self.close_time.hour * 3600 + self.close_time.minute * 60
        return (c - o) / 3600.0

    def bars_per_session(self, interval_seconds: int) -> int:
        return max(1, int(self.hours * 3600 // interval_seconds))


US_EQUITIES = Session("US Equities", "America/New_York", time(9, 30), time(16, 0))
NSE = Session("NSE India", "Asia/Kolkata", time(9, 15), time(15, 30))
CRYPTO = Session("Crypto 24/7", "UTC", time(0, 0), time(23, 59))

_SUFFIX_MAP = {
    ".NS": NSE,
    ".BO": NSE,
    "-USD": CRYPTO,  # e.g. BTC-USD on Yahoo
}


def session_for(ticker: str) -> Session:
    """Resolve the trading session for a ticker (suffix-based)."""
    t = (ticker or "").upper().strip()
    for suffix, session in _SUFFIX_MAP.items():
        if t.endswith(suffix):
            return session
    return US_EQUITIES
