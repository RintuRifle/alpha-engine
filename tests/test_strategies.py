import pytest
from src.strategies.ma_crossover import MACrossover

def test_ma_crossover_signals(sample_ohlcv):
    strategy = MACrossover(short_window=5, long_window=10)
    result = strategy.generate_signals(sample_ohlcv)
    
    assert 'signal' in result.columns
    assert set(result['signal'].unique()).issubset({-1, 0, 1})
