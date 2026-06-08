import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(start="2020-01-01", periods=100)
    df = pd.DataFrame({
        'date': dates,
        'open': np.random.uniform(100, 150, 100),
        'high': np.random.uniform(150, 200, 100),
        'low': np.random.uniform(50, 100, 100),
        'close': np.random.uniform(100, 150, 100),
        'volume': np.random.randint(1000, 10000, 100)
    })
    return df

@pytest.fixture
def mock_config():
    return {
        'initial_capital': 10000.0,
        'commission': 0.001,
        'slippage': 0.0005
    }
