import pytest
from src.backtester.engine import BacktestEngine
from src.strategies.buy_and_hold import BuyAndHold

def test_backtester_engine(sample_ohlcv):
    strategy = BuyAndHold()
    df_signals = strategy.generate_signals(sample_ohlcv)
    
    engine = BacktestEngine(data=df_signals, ticker="TEST")
    portfolio = engine.run()
    
    assert portfolio.cash <= portfolio.initial_capital
    assert len(portfolio.trade_history) > 0
    assert not portfolio.get_equity_df().empty
