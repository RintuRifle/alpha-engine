import pytest
import pandas as pd
from src.analytics.metrics import Metrics

def test_metrics_cagr():
    dates = pd.date_range("2020-01-01", periods=366)
    equity = [10000] * 365 + [11000] # 1 year 10% return
    df = pd.DataFrame({'date': dates, 'total_equity': equity}).set_index('date')
    
    cagr = Metrics.cagr(df)
    assert round(cagr, 2) == 0.10
