"""
Unit tests for the data ingestion layer.

Tests: DataValidator, MarketDataFetcher (mocked), Database round-trip.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from src.data.validator import DataValidator
from src.utils.exceptions import InsufficientDataError


class TestDataValidator:
    """Tests for DataValidator.clean_and_validate()"""

    def test_cleans_nan_values(self, sample_ohlcv):
        """NaN values should be forward-filled then back-filled."""
        df = sample_ohlcv.copy()
        df.loc[5:10, "close"] = None
        df.loc[0:2, "open"] = None

        cleaned = DataValidator.clean_and_validate(df)
        assert not cleaned["close"].isnull().any()
        assert not cleaned["open"].isnull().any()

    def test_fixes_high_less_than_low(self, sample_ohlcv):
        """Rows where high < low should be corrected by swapping."""
        df = sample_ohlcv.copy()
        # Force high < low for a few rows
        df.loc[10, "high"] = 50.0
        df.loc[10, "low"] = 100.0

        cleaned = DataValidator.clean_and_validate(df)
        assert (cleaned["high"] >= cleaned["low"]).all()

    def test_clamps_close_within_range(self, sample_ohlcv):
        """Close price should be clamped to [low, high] range."""
        df = sample_ohlcv.copy()
        df.loc[20, "close"] = df.loc[20, "high"] + 50.0  # Way above high

        cleaned = DataValidator.clean_and_validate(df)
        assert cleaned.loc[20, "close"] <= cleaned.loc[20, "high"]

    def test_fixes_negative_volume(self, sample_ohlcv):
        """Negative volume should be set to 0."""
        df = sample_ohlcv.copy()
        df.loc[15, "volume"] = -1000

        cleaned = DataValidator.clean_and_validate(df)
        assert (cleaned["volume"] >= 0).all()

    def test_raises_on_insufficient_data(self):
        """Should raise InsufficientDataError for very short DataFrames."""
        short_df = pd.DataFrame({
            "date": pd.date_range("2022-01-01", periods=5),
            "open": [100]*5, "high": [110]*5, "low": [90]*5,
            "close": [105]*5, "volume": [1000]*5,
        })

        with pytest.raises(InsufficientDataError):
            DataValidator.clean_and_validate(short_df, min_rows=30)

    def test_raises_on_empty_dataframe(self):
        """Empty DataFrame should raise InsufficientDataError."""
        with pytest.raises(InsufficientDataError):
            DataValidator.clean_and_validate(pd.DataFrame())


class TestMarketDataFetcher:
    """Tests for MarketDataFetcher with mocked yfinance calls."""

    @patch("src.data.fetcher.yf.download")
    def test_fetch_ohlcv_success(self, mock_download):
        """Should return a properly formatted DataFrame on success."""
        mock_df = pd.DataFrame({
            "Open": [100.0], "High": [110.0], "Low": [90.0],
            "Close": [105.0], "Volume": [1000000],
        }, index=pd.DatetimeIndex(["2022-01-03"], name="Date"))
        mock_download.return_value = mock_df

        from src.data.fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher(rate_limit_seconds=0)
        result = fetcher.fetch_ohlcv("AAPL", "2022-01-01", "2022-01-05")

        assert "close" in result.columns
        assert "date" in result.columns
        assert len(result) == 1

    @patch("src.data.fetcher.yf.download")
    def test_fetch_ohlcv_empty_raises(self, mock_download):
        """Should raise DataFetchError when no data is returned."""
        mock_download.return_value = pd.DataFrame()

        from src.data.fetcher import MarketDataFetcher
        from src.utils.exceptions import DataFetchError
        fetcher = MarketDataFetcher(rate_limit_seconds=0)

        with pytest.raises(DataFetchError):
            fetcher.fetch_ohlcv("INVALID", "2022-01-01", "2022-01-05")
