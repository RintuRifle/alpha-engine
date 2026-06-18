"""
Report generator using QuantStats for HTML tear sheet generation.

Generates comprehensive performance reports with charts, metrics tables,
and benchmark comparison. Output is a self-contained HTML file.
"""

import os
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates HTML tear sheets using the QuantStats library."""

    @staticmethod
    def generate_tearsheet(
        equity_df: pd.DataFrame,
        benchmark_ticker: str = "SPY",
        output_file: str = "reports/tearsheets/report.html",
        title: str = "Quant Research Platform — Tear Sheet",
    ) -> bool:
        """
        Generate a QuantStats HTML tear sheet.

        Args:
            equity_df: Portfolio equity DataFrame with 'total_equity' column.
            benchmark_ticker: Benchmark ticker for comparison.
            output_file: Path to save the HTML report.
            title: Title for the report.

        Returns:
            True if report was generated successfully, False otherwise.
        """
        if equity_df.empty:
            logger.warning("Cannot generate tearsheet: empty equity DataFrame")
            return False

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate returns from equity curve
        returns = equity_df["total_equity"].pct_change().dropna()

        # Make index timezone-naive (QuantStats requirement)
        if returns.index.tz is not None:
            returns.index = returns.index.tz_localize(None)

        try:
            import quantstats as qs

            qs.reports.html(
                returns,
                benchmark=benchmark_ticker,
                output=str(output_path),
                title=title,
            )
            logger.info(f"Tear sheet saved to: {output_path.resolve()}")
            return True

        except ImportError:
            logger.error("QuantStats not installed. Run: pip install quantstats")
            return False
        except Exception as e:
            logger.error(f"Failed to generate tear sheet: {e}")
            return False
