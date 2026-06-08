import quantstats as qs
import pandas as pd

class ReportGenerator:
    @staticmethod
    def generate_tearsheet(equity_df: pd.DataFrame, benchmark_ticker: str = "SPY", output_file: str = "tearsheets/report.html"):
        if equity_df.empty: return
        returns = equity_df['total_equity'].pct_change().dropna()
        # Make index timezone naive if it has timezone
        if returns.index.tz is not None:
            returns.index = returns.index.tz_localize(None)
            
        try:
            qs.reports.html(returns, benchmark=benchmark_ticker, output=output_file, title='Quant Research Tear Sheet')
        except Exception as e:
            print(f"Failed to generate QuantStats report: {e}")
