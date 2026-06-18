"""
Data validation and cleaning for OHLCV market data.

Handles NaN filling, sanity checks (high >= low, close within range),
volume validation, and minimum data length requirements.
"""

import pandas as pd

from src.utils.exceptions import InsufficientDataError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """Validates and cleans OHLCV DataFrames before they're used in strategies."""

    @staticmethod
    def clean_and_validate(
        df: pd.DataFrame, min_rows: int = 30
    ) -> pd.DataFrame:
        """
        Clean and validate OHLCV data. Applies forward-fill, sanity checks,
        and raises errors for insufficient data.

        Args:
            df: Raw OHLCV DataFrame.
            min_rows: Minimum number of rows required after cleaning.

        Returns:
            Cleaned DataFrame.

        Raises:
            InsufficientDataError: If DataFrame has fewer rows than min_rows.
        """
        if df.empty:
            raise InsufficientDataError(
                "Received empty DataFrame", required=min_rows, available=0
            )

        df = df.copy()
        logger.info(f"Validating data: {len(df)} rows, columns={list(df.columns)}")

        # ── Step 1: Verify expected columns exist ──
        expected_cols = ["date", "open", "high", "low", "close", "volume"]
        missing = [col for col in expected_cols if col not in df.columns]
        if missing:
            logger.warning(f"Missing columns: {missing}")

        # ── Step 2: Handle missing values ──
        numeric_cols = ["open", "high", "low", "close", "volume"]
        available_numeric = [c for c in numeric_cols if c in df.columns]

        nan_counts = df[available_numeric].isnull().sum()
        total_nans = nan_counts.sum()
        if total_nans > 0:
            logger.warning(f"Found {total_nans} NaN values: {nan_counts[nan_counts > 0].to_dict()}")

        # Forward-fill first (carry previous day's value), then back-fill any remaining
        df[available_numeric] = df[available_numeric].ffill()
        df[available_numeric] = df[available_numeric].bfill()

        # ── Step 3: OHLCV sanity checks ──
        if "high" in df.columns and "low" in df.columns:
            invalid_hl = df[df["high"] < df["low"]]
            if not invalid_hl.empty:
                logger.warning(
                    f"Found {len(invalid_hl)} rows where High < Low — correcting"
                )
                # Fix by swapping high and low where invalid
                mask = df["high"] < df["low"]
                df.loc[mask, ["high", "low"]] = df.loc[mask, ["low", "high"]].values

        if "close" in df.columns and "high" in df.columns and "low" in df.columns:
            # Close should be within [low, high] range
            invalid_close = df[(df["close"] > df["high"]) | (df["close"] < df["low"])]
            if not invalid_close.empty:
                logger.warning(
                    f"Found {len(invalid_close)} rows where Close is outside [Low, High] — clamping"
                )
                df["close"] = df["close"].clip(lower=df["low"], upper=df["high"])

        if "volume" in df.columns:
            # Volume should be non-negative
            neg_volume = df[df["volume"] < 0]
            if not neg_volume.empty:
                logger.warning(f"Found {len(neg_volume)} rows with negative volume — setting to 0")
                df.loc[df["volume"] < 0, "volume"] = 0

            # Zero-volume days are suspicious but not necessarily wrong
            zero_volume = df[df["volume"] == 0]
            if len(zero_volume) > len(df) * 0.1:  # More than 10% zero-volume days
                logger.warning(
                    f"{len(zero_volume)} zero-volume days ({len(zero_volume)/len(df)*100:.1f}%) — data quality concern"
                )

        # ── Step 4: Minimum data length check ──
        if len(df) < min_rows:
            raise InsufficientDataError(
                f"Only {len(df)} rows after cleaning (need {min_rows})",
                required=min_rows,
                available=len(df),
            )

        logger.info(f"Validation complete: {len(df)} clean rows")
        return df
